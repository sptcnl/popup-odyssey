import { useState, useEffect, useCallback } from 'react'
import MapView from './components/MapView'
import PopupList from './components/PopupList'
import FilterBar from './components/FilterBar'
import { storesApi } from './api/stores'
import LoginModal from './components/LoginModal'
import AddPlaceModal from './components/AddPlaceModal'

export default function App() {
  // 📍 상태들
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

  // 🚀 fetchPlaces - camelCase + 실제 현재시간
  const fetchPlaces = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const apiPlaces = await storesApi.getPlaces()
      console.log('📡 API 데이터:', apiPlaces.length, apiPlaces[0])

      const now = new Date()  // ✅ 실제 현재 시간

      const mapped = apiPlaces
        .map((p) => {
          const lat = Number(p.geoY)
          const lng = Number(p.geoX)

          if (!lat || !lng || isNaN(lat) || isNaN(lng)) {
            console.warn('❌ 좌표 없음:', p.name)
            return null
          }

          const base = {
            id: p.id,
            name: p.name,
            address: p.address,
            categories: p.detailCategory ? [p.detailCategory] : [],
            latlng: [lat, lng],
            isPopup: !!p.isPopup,      // ✅ camelCase
            isPublic: !!p.isPublic,    // ✅ camelCase
            myPlace: !!p.myPlace,      // ✅ camelCase
            userId: p.user || null,
          }

          console.log('🎯', p.name, {
            isPopup: p.isPopup,
            isPublic: p.isPublic,
            myPlace: p.myPlace
          })

          // 🔥 팝업: 종료된 것만 필터링
          if (p.isPopup) {
            if (p.endDate) {
              const endDate = new Date(p.endDate)
              if (endDate < now) {
                console.log('⏰ 종료:', p.name)
                return null
              }
            }

            return {
              ...base,
              startDate: p.startDate,
              endDate: p.endDate,
              status: p.startDate && new Date(p.startDate) > now 
                ? '⏰진행 예정' : '🔥진행 중',
            }
          }

          return base  // 일반 장소 무조건 통과
        })
        .filter(Boolean)

      console.log('✅ 최종 places:', mapped.length)
      console.log('📊 통계:', {
        total: mapped.length,
        popup: mapped.filter(p => p.isPopup).length,
        normal: mapped.filter(p => !p.isPopup).length,
        myPlaces: mapped.filter(p => p.myPlace).length
      })
      
      setPlaces(mapped)
    } catch (e) {
      console.error('❌ 에러:', e)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // 🔥 로그인 상태 변경시 재조회
  useEffect(() => {
    if (isLoggedIn) {
      console.log('🔄 로그인 → 내 비공개 포함 재조회')
      fetchPlaces()
    }
  }, [isLoggedIn, fetchPlaces])

  // 🚀 최초 로드
  useEffect(() => {
    fetchPlaces()
  }, [fetchPlaces])

  // ✅ 선택 토글
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
      
      console.log('✅ 경로 최적화:', result)
      setRouteData({
        ...result,
        selectedPlaces,
        routeVersion: Date.now()
      })
      alert(`${result.nLocations}개 → 최적화 완료!`)
    } catch (e) {
      console.error(e)
      alert('경로 최적화 실패: ' + e.message)
    } finally {
      setIsOptimizing(false)
    }
  }

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

  const handlePlaceAdded = async () => {
    await fetchPlaces()
    setShowAddModal(false)
  }

  // 🔥 완벽한 필터링 (내 비공개 장소 포함)
  const filteredPlaces = places.filter(p => {
    // 1️⃣ 팝업/일반 분류
    if (placeType === 'popup' && !p.isPopup) return false
    if (placeType === 'normal' && p.isPopup) return false

    // 2️⃣ 핵심! 로그인시 내 비공개 장소 표시
    if (!p.isPublic && (!isLoggedIn || !p.myPlace)) {
      console.log('❌ 비공개 제외:', p.name, {isPublic: p.isPublic, myPlace: p.myPlace})
      return false
    }

    // 3️⃣ 카테고리 필터 (팝업 + 일반 공통)
    if (selectedCategory && selectedCategory !== '') {
      return p.categories.includes(selectedCategory)
    }

    // 4️⃣ 검색
    if (searchQuery) {
      return (
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.address.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    return true
  })

  useEffect(() => {
    setSelectedCategory('')
  }, [placeType])

  const categoryList = Array.from(
    new Set(
      places
        .filter(p => !p.isPopup)
        .flatMap(p => p.categories)
        .filter(Boolean)
    )
  )

  if (loading) return <div className="app" style={{padding: '40px', fontSize: '16px'}}>데이터 불러오는 중...</div>
  if (error) return <div className="app" style={{padding: '40px', color: 'red'}}>에러: {error}</div>

  return (
    <div className="app" style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'row',
      fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
      overflow: 'hidden',
    }}>
      {/* 지도 영역 */}
      <div style={{ flex: 3, height: '100vh', position: 'relative' }}>
        <MapView
          key={routeData?.routeVersion || 'map'}
          popups={filteredPlaces}
          selectedIds={selectedIds.filter(id => filteredPlaces.some(p => p.id === id))}
          onSelect={toggleSelection}
          routeData={routeData}
        />

        {/* 플로팅 버튼 */}
        <div style={{
          position: 'fixed',
          bottom: '60px',
          right: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          zIndex: 2000,
        }}>
          <button
            onClick={handleAddPlace}
            style={{
              background: isLoggedIn ? '#228be6' : '#535353',
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
            <button disabled style={{ 
              background: '#6b7280', color: 'white', borderRadius: '50%', 
              width: '56px', height: '56px', border: 'none', 
              cursor: 'not-allowed', fontSize: '20px' 
            }}>⏳</button>
          ) : routeData ? (
            <button onClick={clearRoute} style={{ 
              background: '#ef4444', color: 'white', borderRadius: '50%', 
              width: '56px', height: '56px', border: 'none', 
              cursor: 'pointer', fontSize: '20px' 
            }} title="경로 초기화">✕</button>
          ) : selectedIds.length >= 2 ? (
            <button onClick={handleOptimizeRoute} style={{ 
              background: '#228be6', color: 'white', borderRadius: '50%', 
              width: '56px', height: '56px', border: 'none', 
              cursor: 'pointer', fontSize: '20px' 
            }} title="경로 찾기">🧭</button>
          ) : (
            <button disabled style={{ 
              background: '#ccc', color: 'white', borderRadius: '50%', 
              width: '56px', height: '56px', border: 'none', 
              cursor: 'not-allowed', fontSize: '20px' 
            }}>🧭</button>
          )}
        </div>
      </div>

      {/* 사이드바 */}
      <div className="sidebar" style={{ width: '360px', display: 'flex', flexDirection: 'column' }}>
        {/* 팝업/일반 토글 */}
        <div style={{ display: 'flex', borderBottom: '1px solid #e9ecef' }}>
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
            🔥 팝업 ({places.filter(p => p.isPopup).length})
          </button>

          <button
            onClick={() => {
              setPlaceType('normal')
              setSelectedCategory(null)
            }}
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
            🏠 일반 ({places.filter(p => !p.isPopup).length})
          </button>
        </div>

        {/* 검색 */}
        <FilterBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
          popups={places}
          filteredCount={filteredPlaces.length}
          placeType={placeType}
        />

        {/* 리스트 */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <PopupList
            popups={filteredPlaces}
            selectedIds={selectedIds}
            onSelect={toggleSelection}
          />
        </div>

        {/* 하단 상태 */}
        <div style={{
          padding: '12px',
          fontSize: '12px',
          textAlign: 'center',
          color: '#868e96',
          borderTop: '1px solid #e9ecef',
        }}>
          {placeType === 'popup' && <>🦍 data by 성수동 고릴라 <br /></>}
          총 {filteredPlaces.length}개 · 선택 {selectedIds.length}/30
          {isLoggedIn && (
            <> · <span style={{color: '#f59e0b'}}>
              내장소 {places.filter(p => p.myPlace).length}개
            </span></>
          )}
        </div>
      </div>

      {/* 모달들 */}
      {showLoginModal && (
        <LoginModal
          onClose={() => setShowLoginModal(false)}
          onSuccess={(user) => {
            console.log('🎉 로그인 성공:', user)
            setIsLoggedIn(true)
            setUser(user)
            setShowLoginModal(false)
            setShowAddModal(true)
          }}
        />
      )}

      {showAddModal && (
        <AddPlaceModal
          onClose={() => setShowAddModal(false)}
          onSuccess={handlePlaceAdded}
        />
      )}
    </div>
  )
}