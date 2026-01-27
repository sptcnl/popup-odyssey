export default function PopupCard({ popup, selected, onClick }) {
  return (
    <div
      className={`card ${selected ? 'selected' : ''}`}
      onClick={onClick}
    >
      {/* 배경 어두운 오버레이 */}
      <div className="card-overlay" />

      {/* 콘텐츠 영역 */}
      <div className="card-content" style={{ padding: '1px 12px 12px 16px' }}>
        <h3>{popup.name}</h3>

        {/* ✅ 팝업일 때만 기간 / 상태 표시 */}
        {popup.isPopup && (
          <>
            <small>
              {popup.startDate} ~ {popup.endDate} · {popup.status}
            </small>
            <br />
          </>
        )}

        <p>{popup.address}</p>

        {/* 카테고리 */}
        {popup.detailCategory && (
          <small># {popup.detailCategory}</small>
        )}
      </div>
    </div>
  )
}