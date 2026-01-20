export default function PopupCard({ popup, selected, onClick }) {
  return (
    <div
      className={`card ${selected ? 'selected' : ''}`}
      onClick={onClick}
      
    >
      {/* 배경 어두운 오버레이 */}
      <div className="card-overlay" />
      
      {/* 콘텐츠 영역 */}
      <div className="card-content">
        <h3>{popup.name}</h3>
        <small>{popup.startDate} - {popup.endDate} : {popup.status}</small>
        <br/>
        <p>{popup.address}</p>
        <small># {popup.detailCategory}</small>
      </div>
    </div>
  )
}