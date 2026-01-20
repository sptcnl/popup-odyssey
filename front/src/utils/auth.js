export const kakaoLoginRedirectUrl = () => {
  const REST_API_KEY = import.meta.env.VITE_KAKAO_REST_API_KEY
  const redirectUri = `${window.location.origin}/oauth/callback`
  const AUTH_URL = `https://kauth.kakao.com/oauth/authorize?response_type=code&client_id=${REST_API_KEY}&redirect_uri=${encodeURIComponent(redirectUri)}`

  window.location.href = AUTH_URL
}