import { useEffect } from "react"

export default function LoginModal({ onClose, onSuccess }) {

  useEffect(() => {
    if (window.Kakao && !window.Kakao.isInitialized()) {
      window.Kakao.init(import.meta.env.VITE_KAKAO_JS_KEY)
    }
  }, [])

  const handleKakaoLogin = async () => {
    if (!window.Kakao) return alert("카카오 SDK 로드 실패");

    window.Kakao.Auth.login({
      scope: "profile_nickname",
      success: async (authObj) => {
          try {
              console.log("카카오 access_token:", authObj.access_token);
              
              const res = await fetch("http://localhost:8000/api/accounts/auth/kakao/", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ 
                      access_token: authObj.access_token  // 이미 올바른 값!
                  }),
              });

              if (!res.ok) {
                  const errorData = await res.json();
                  console.error("서버 응답:", errorData);
                  throw new Error(errorData.error || "서버 로그인 실패");
              }
              
              const data = await res.json();
              console.log("로그인 성공:", data);

              // JWT + user 정보 저장
              localStorage.setItem("access", data.access);
              localStorage.setItem("refresh", data.refresh);
              localStorage.setItem("user", JSON.stringify(data.user));

              onSuccess?.(data.user); // 부모(App)에게 알림
              onClose(); // 모달 닫기
              
          } catch (err) {
              console.error("로그인 오류:", err);
              alert(`로그인 처리 중 오류 발생: ${err.message}`);
          }
      },
      fail: (err) => {
          console.error("카카오 SDK 로그인 실패:", err);
          alert("카카오 로그인 실패");
      },
    });
  };


  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <h3>로그인</h3>
        <button onClick={handleKakaoLogin} style={kakaoBtn}>카카오 로그인</button>
        <button onClick={onClose} style={subBtn}>닫기</button>
      </div>
    </div>
  )
}

/* ===== styles ===== */
const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 3000 }
const modalStyle = { background: "white", padding: 24, borderRadius: 12, width: 320, display: "flex", flexDirection: "column", gap: 14 }
const kakaoBtn = { background: "#FEE500", color: "#191919", border: "none", padding: 12, borderRadius: 8, fontSize: 15, fontWeight: "bold", cursor: "pointer" }
const subBtn = { background: "#e9ecef", border: "none", padding: 10, borderRadius: 8, cursor: "pointer" }