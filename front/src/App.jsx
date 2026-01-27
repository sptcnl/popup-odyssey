import { useState, useEffect } from 'react'
import MapView from './components/MapView'
import PopupList from './components/PopupList'
import FilterBar from './components/FilterBar'
import { storesApi } from './api/stores'
import LoginModal from './components/LoginModal'
import AddPlaceModal from './components/AddPlaceModal'

export default function App() {
  const [selectedIds, setSelectedIds] = useState([])
  const [places, setPlaces] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [routeData, setRouteData] = useState(null)
  const [isOptimizing, setIsOptimizing] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [user, setUser] = useState(null)
  const [placeType, setPlaceType] = useState('popup')

  const toggleSelection = (id) => {
    setSelectedIds((prev) => {
      const isSelected = prev.includes(id)
      if (isSelected) return prev.filter((sid) => sid !== id)
      if (prev.length < 30) return [...prev, id]
      alert('최대 30개까지만 선택 가능합니다!')
      return prev
    })
  }

  // ✅ 경로 최적화
  const handleOptimizeRoute = async () => {
    if (selectedIds.length < 2) {
      alert('2개 이상의 장소를 선택해주세요!')
      return
    }

    setIsOptimizing(true)
    setRouteData(null)
    try {
      const selectedPlaces = places.filter((p) => selectedIds.includes(p.id))
      const coordinates = selectedPlaces.map(p => p.latlng)
      const result = await storesApi.optimizeRoute({ coordinates })
      
      console.log('✅ 경로 최적화 결과:', result)
      setRouteData({
        ...result,
        selectedPlaces,
        routeVersion: Date.now()
      })
      alert(`${result.nLocations}개 → 최적화 완료! 지도 확인하세요.`)
    } catch (e) {
      console.error(e)
      alert('경로 최적화 실패: ' + e.message)
    } finally {
      setIsOptimizing(false)
    }
  }

  // ✅ 경로 초기화
  const clearRoute = () => {
    setRouteData(null)
  }

  const handleAddPlace = () => {
    if (!isLoggedIn) {
      setShowLoginModal(true)
      return
    }
    setShowAddModal(true)
  }

  useEffect(() => {
    const fetchPlaces = async () => {
      try {
        setLoading(true)
        setError(null)
        const places = await storesApi.getPlaces()
        const now = new Date()
        
        // ✅ 이미 지난 팝업 필터링
        const mapped = places
          .map((p) => {
            const lat = p.geoY
            const lng = p.geoX
            if (!lat || !lng) return null

            const base = {
              id: p.id,
              name: p.name,
              address: p.address,
              categories: p.categories || [],
              latlng: [lat, lng],
              isPopup: p.isPopup,
            }

            // ✅ 팝업일 때만 기간/상태 부여
            if (p.isPopup) {
              const now = new Date()
              const start = new Date(p.startDate)
              const end = new Date(p.endDate)

              if (end < now) return null // 종료된 팝업 제외

              return {
                ...base,
                startDate: p.startDate,
                endDate: p.endDate,
                status: now < start ? '⏰진행 예정' : '🔥진행 중',
              }
            }

            // ✅ 일반 장소
            return base
          })
          .filter(Boolean)
        setPlaces(mapped)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    fetchPlaces()
  }, [])

  const filteredPlaces = places.filter(p => {
    // 1️⃣ 팝업 / 일반 분리
    if (placeType === 'popup' && !p.isPopup) return false
    if (placeType === 'normal' && p.isPopup) return false

    // 2️⃣ 일반 장소 + 카테고리 필터
    if (placeType === 'normal' && selectedCategory) {
      return p.categories.includes(selectedCategory)
    }

    // 3️⃣ 검색
    if (searchQuery) {
      return (
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.address.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    return true
  })

  const categoryList = Array.from(
    new Set(
      places
        .filter(p => !p.isPopup)
        .flatMap(p => p.categories)
    )
  )

  if (loading) return <div className="app" style={{padding: '40px', fontSize: '16px'}}>데이터 불러오는 중...</div>
  if (error) return <div className="app" style={{padding: '40px', color: 'red'}}>에러: {error}</div>

  return (
    <div
      className="app"
      style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'row',
        fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* ===================== 지도 ===================== */}
      <div style={{ flex: 3, height: '100vh', position: 'relative' }}>
        <MapView
          key={routeData?.routeVersion || 'map'}
          popups={filteredPlaces}
          selectedIds={selectedIds.filter(id =>
            filteredPlaces.some(p => p.id === id)
          )}
          onSelect={toggleSelection}
          routeData={routeData}
        />

        {/* ================= 플로팅 버튼 ================= */}
        <div
          style={{
            position: 'fixed',
            bottom: '60px',
            right: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            zIndex: 2000,
          }}
        >
          <button
            onClick={handleAddPlace}
            style={{
              background: '#535353',
              color: 'white',
              borderRadius: '50%',
              width: '56px',
              height: '56px',
              border: 'none',
              cursor: 'pointer',
              fontSize: '24px',
              fontWeight: 'bold',
              boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
            }}
            title="장소 추가"
          >
            ＋
          </button>

          {isOptimizing ? (
            <button
              disabled
              style={{
                background: '#6b7280',
                color: 'white',
                borderRadius: '50%',
                width: '56px',
                height: '56px',
                border: 'none',
                cursor: 'not-allowed',
                fontSize: '20px',
              }}
            >
              ⏳
            </button>
          ) : routeData ? (
            <button
              onClick={clearRoute}
              style={{
                background: '#ef4444',
                color: 'white',
                borderRadius: '50%',
                width: '56px',
                height: '56px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '20px',
              }}
              title="경로 초기화"
            >
              ✕
            </button>
          ) : selectedIds.length >= 2 ? (
            <button
              onClick={handleOptimizeRoute}
              style={{
                background: '#228be6',
                color: 'white',
                borderRadius: '50%',
                width: '56px',
                height: '56px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '20px',
              }}
              title="경로 찾기"
            >
              🧭
            </button>
          ) : (
            <button
              disabled
              style={{
                background: '#ccc',
                color: 'white',
                borderRadius: '50%',
                width: '56px',
                height: '56px',
                border: 'none',
                cursor: 'not-allowed',
                fontSize: '20px',
              }}
            >
              🧭
            </button>
          )}
        </div>
      </div>

      {/* ===================== 사이드바 ===================== */}
      <div className="sidebar" style={{ width: '360px', display: 'flex', flexDirection: 'column' }}>
        
        {/* ===== 팝업 / 일반 토글 ===== */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #e9ecef',
          }}
        >
          <button
            onClick={() => {
              setPlaceType('popup')
              setSelectedCategory(null)
            }}
            style={{
              flex: 1,
              padding: '14px',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              background: placeType === 'popup' ? '#212529' : '#f8f9fa',
              color: placeType === 'popup' ? 'white' : '#495057',
            }}
          >
            🔥 팝업
          </button>

          <button
            onClick={() => setPlaceType('normal')}
            style={{
              flex: 1,
              padding: '14px',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              background: placeType === 'normal' ? '#212529' : '#f8f9fa',
              color: placeType === 'normal' ? 'white' : '#495057',
            }}
          >
            🏠 일반
          </button>
        </div>

        {/* ===== 검색 ===== */}
        <FilterBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
          popups={filteredPlaces}
          filteredCount={filteredPlaces.length}
        />

        {/* ===== 일반 장소일 때만 카테고리 ===== */}
        {placeType === 'normal' && (
          <div
            style={{
              padding: '12px',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px',
              borderBottom: '1px solid #e9ecef',
            }}
          >
            {categoryList.map(cat => (
              <button
                key={cat}
                onClick={() =>
                  setSelectedCategory(selectedCategory === cat ? null : cat)
                }
                style={{
                  padding: '6px 10px',
                  borderRadius: '16px',
                  border: '1px solid #dee2e6',
                  background: selectedCategory === cat ? '#228be6' : 'white',
                  color: selectedCategory === cat ? 'white' : '#495057',
                  fontSize: '13px',
                  cursor: 'pointer',
                }}
              >
                {cat}
              </button>
            ))}
          </div>
        )}

        {/* ===== 리스트 ===== */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <PopupList
            popups={filteredPlaces}
            selectedIds={selectedIds}
            onSelect={toggleSelection}
          />
        </div>

        {/* ===== 하단 ===== */}
        <div
          style={{
            padding: '12px',
            fontSize: '12px',
            textAlign: 'center',
            color: '#868e96',
            borderTop: '1px solid #e9ecef',
          }}
        >
          {placeType === 'popup' && (
            <>
              🦍 data by 성수동 고릴라 <br />
            </>
          )}
          총 {filteredPlaces.length}개 · 선택 {selectedIds.length}/30
        </div>
      </div>

      {/* ===================== 모달 ===================== */}
      {showLoginModal && (
        <LoginModal
          onClose={() => setShowLoginModal(false)}
          onSuccess={(user) => {
            setIsLoggedIn(true)
            setUser(user)
            setShowAddModal(true)
          }}
        />
      )}

      {showAddModal && (
        <AddPlaceModal onClose={() => setShowAddModal(false)} />
      )}
    </div>
  )
}