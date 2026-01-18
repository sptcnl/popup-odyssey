import PopupCard from './PopupCard'

export default function PopupList({ popups, selectedIds, onSelect }) {  // ✅ selectedId → selectedIds
  return (
    <div className="list">
      {popups.map(p => (
        <PopupCard
          key={p.id}
          popup={p}
          selected={selectedIds.includes(p.id)}  // ✅ 배열 체크
          onClick={() => onSelect(p.id)}
        />
      ))}
    </div>
  )
}