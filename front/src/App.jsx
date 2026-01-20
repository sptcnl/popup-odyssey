import { useState, useEffect } from 'react'
import MapView from './components/MapView'
import PopupList from './components/PopupList'
import FilterBar from './components/FilterBar'
import { storesApi } from './api/stores'

export default function App() {
  const [selectedIds, setSelectedIds] = useState([])
  const [popups, setPopups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [routeData, setRouteData] = useState(null)
  const [isOptimizing, setIsOptimizing] = useState(false)

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
    try {
      const selectedPlaces = popups.filter((p) => selectedIds.includes(p.id))
      const coordinates = selectedPlaces.map(p => p.latlng)
      const result = await storesApi.optimizeRoute({ coordinates })
      
      console.log('✅ 경로 최적화 결과:', result)
      setRouteData(result)
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
    alert('새로운 장소 추가 기능은 아직 준비 중입니다!')
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
            if (!lat || !lng) {
              console.warn(`⚠️ 좌표 없는 팝업 건너뜀:`, p.name, p.id)
              return null
            }
            
            // 종료일이 오늘보다 이전이면 제외
            const endDate = new Date(p.endDate)
            if (endDate < now) {
              console.log(`⏰ 이미 종료된 팝업 제외:`, p.name)
              return null
            }
            
            return {
              id: p.id,
              name: p.name,
              address: p.address,
              startDate: p.startDate,
              endDate: p.endDate,
              detailCategory: p.detailCategory || 'popup',
              latlng: [lat, lng],
            }
          })
          .filter(Boolean)
        setPopups(mapped)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    fetchPlaces()
  }, [])

  const filteredPopups = popups.filter((p) => {
    const matchesSearch = !searchQuery || 
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.address.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = !selectedCategory || p.detailCategory === selectedCategory
    return matchesSearch && matchesCategory
  })

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
      {/* 지도 */}
      <div style={{ flex: 3, height: '100vh', position: 'relative' }}>
        <MapView
          popups={filteredPopups}
          selectedIds={selectedIds.filter(id => filteredPopups.some(p => p.id === id))}
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
          <button onClick={handleAddPlace} style={{
            background: '#535353', color: 'white', borderRadius: '50%',
            width: '56px', height: '56px', border: 'none', cursor: 'pointer',
            fontSize: '24px', fontWeight: 'bold', boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
            transition: 'all 0.2s',
          }} title="장소 추가">＋</button>
          
          {/* ✅ 로딩중/완료 상태에 따른 버튼 전환 */}
          {isOptimizing ? (
            <button disabled style={{
              background: '#6b7280', color: 'white',
              borderRadius: '50%', width: '56px', height: '56px', border: 'none',
              cursor: 'not-allowed', fontSize: '20px', boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
            }} title="최적화 중...">
              ⏳
            </button>
          ) : routeData ? (
            <button onClick={clearRoute} style={{
              background: '#ef4444', color: 'white', borderRadius: '50%',
              width: '56px', height: '56px', border: 'none', cursor: 'pointer',
              fontSize: '20px', fontWeight: 'bold', boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
              transition: 'all 0.2s',
            }} title="경로 초기화">
              ❌
            </button>
          ) : selectedIds.length >= 2 ? (
            <button onClick={handleOptimizeRoute} style={{
              background: '#228be6', color: 'white', borderRadius: '50%',
              width: '56px', height: '56px', border: 'none', cursor: 'pointer',
              fontSize: '20px', boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
              transition: 'all 0.2s',
            }} title="경로 찾기">
              🧭
            </button>
          ) : (
            <button disabled style={{
              background: '#ccc', color: 'white', borderRadius: '50%',
              width: '56px', height: '56px', border: 'none', cursor: 'not-allowed',
              fontSize: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.15)',
            }} title="2개 이상 선택">
              🧭
            </button>
          )}
        </div>
      </div>

      {/* 사이드바 */}
      <div style={{
        width: '25%', height: '100vh', display: 'flex', flexDirection: 'column',
        background: '#fafbfc', borderLeft: '1px solid #e1e5e9', overflow: 'hidden',
      }}>
        <div style={{ flex: '0 0 auto' }}>
          <FilterBar
            searchQuery={searchQuery} onSearchChange={setSearchQuery}
            selectedCategory={selectedCategory} onCategoryChange={setSelectedCategory}
            popups={popups} filteredCount={filteredPopups.length}
          />
        </div>
        
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden' }}>
          <PopupList popups={filteredPopups} selectedIds={selectedIds} onSelect={toggleSelection} />
        </div>

        <div style={{ flex: '0 0 auto', background: '#f8f9fa', borderTop: '1px solid #e9ecef',
          padding: '12px', textAlign: 'center', fontSize: '13px', color: '#6c757d', fontWeight: 500 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <span style={{ width: '24px', height: '24px', background: '#fffcec', borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px',
              color: '#f59e0b', fontWeight: 'bold' }}>🦍</span>
            <span>data by 성수동 고릴라</span>
            <span style={{ fontSize: '12px', color: '#adb5bd' }}>
              • 총 {popups.length}개 • 선택 {selectedIds.length}/30
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}