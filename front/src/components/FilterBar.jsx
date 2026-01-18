// components/FilterBar.jsx
export default function FilterBar({ 
  searchQuery, 
  onSearchChange, 
  selectedCategory, 
  onCategoryChange, 
  popups, 
  filteredCount 
}) {
  const categories = Array.from(
    new Set(popups.map(p => p.detailCategory).filter(Boolean))
  ).sort()

  return (
    <div 
      style={{
        padding: '20px 12px 16px',  // ✅ 오른쪽 패딩 16→12px
        background: 'white',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      {/* ✅ 검색 입력 - 완벽 수정 */}
      <input
        type="text"
        placeholder="🔍 팝업명 / 주소 / 키워드 검색"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{
          width: '100%',
          padding: '12px 16px',
          border: '2px solid #e5e7eb',
          borderRadius: '12px',
          fontSize: '15px',
          outline: 'none',
          transition: 'all 0.2s ease',
          background: '#fafbfc',
          boxSizing: 'border-box',        // ⭐ 필수 1위
          display: 'block',               // ⭐ 필수 2위
        }}
        onFocus={(e) => {
          e.target.style.borderColor = '#3b82f6'
          e.target.style.background = 'white'
          e.target.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.1)'
        }}
        onBlur={(e) => {
          e.target.style.borderColor = '#e5e7eb'
          e.target.style.background = '#fafbfc'
          e.target.style.boxShadow = 'none'
        }}
      />

      {/* ✅ 카테고리 row 수정 */}
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <select
          value={selectedCategory}
          onChange={(e) => onCategoryChange(e.target.value)}
          style={{
            flex: 1,                      // ✅ 그대로
            padding: '10px 12px',         // ✅ 좌우 패딩 14→12px
            border: '2px solid #e5e7eb',
            borderRadius: '10px',
            background: '#fafbfc',
            fontSize: '14px',
            cursor: 'pointer',
            outline: 'none',
            transition: 'all 0.2s ease',
            boxSizing: 'border-box',      // ⭐ 추가
          }}
          onFocus={(e) => {
            e.target.style.borderColor = '#3b82f6'
            e.target.style.background = 'white'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = '#e5e7eb'
            e.target.style.background = '#fafbfc'
          }}
        >
          <option value="">🏷️ 전체 카테고리</option>
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>

        <div
          style={{
            fontSize: '13px',
            color: '#6b7280',
            background: '#f3f4f6',
            padding: '6px 12px',
            borderRadius: '20px',
            fontWeight: '500',
            minWidth: '72px',             // ✅ 80→72px
            textAlign: 'center',
            whiteSpace: 'nowrap',         // ✅ 추가
            flexShrink: 0,                // ✅ 추가 (수축 방지)
          }}
        >
          {filteredCount}/{popups.length}
        </div>
      </div>

      {/* 초기화 버튼 */}
      {(searchQuery || selectedCategory) && (
        <button
          onClick={() => {
            onSearchChange('')
            onCategoryChange('')
          }}
          style={{
            padding: '10px 16px',
            background: '#fef2f2',
            color: '#dc2626',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '500',
            transition: 'all 0.2s',
            boxSizing: 'border-box',      // ⭐ 추가
          }}
          onMouseOver={(e) => {
            e.target.style.background = '#fee2e2'
            e.target.style.transform = 'translateY(-1px)'
          }}
          onMouseOut={(e) => {
            e.target.style.background = '#fef2f2'
            e.target.style.transform = 'none'
          }}
        >
          🔄 필터 초기화
        </button>
      )}
    </div>
  )
}