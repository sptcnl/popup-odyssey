import { useEffect, useRef } from 'react'

export default function MapView({ popups, selectedIds, onSelect, routeData }) {
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  const markers = useRef([])
  const routeLayer = useRef(null)
  const orderMarkers = useRef([])
  const logoRef = useRef(null)

  /* ======================
     지도 초기화
  ====================== */
  useEffect(() => {
    if (!window.L) return

    mapInstance.current = window.L
      .map(mapRef.current)
      .setView([37.5445, 127.0557], 13)

    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
    }).addTo(mapInstance.current)

    // 로고
    const timer = setTimeout(() => {
      if (mapRef.current && !logoRef.current) {
        const logoDiv = document.createElement('div')
        logoDiv.style.cssText = `
          position: absolute; top: 10px; left: 10px; z-index: 1000;
          width: 120px; height: 36px;
          background: #000; border-radius: 10px;
          display: flex; align-items: center; justify-content: center;
          color: white; font-weight: 700; font-size: 11px;
          box-shadow: 0 4px 16px rgba(0,0,0,0.25);
          pointer-events: none;
        `
        logoDiv.innerHTML = '🚶‍➡️ 팝업순례'
        mapRef.current.appendChild(logoDiv)
        logoRef.current = logoDiv
      }
    }, 100)

    return () => {
      clearTimeout(timer)
      if (logoRef.current) logoRef.current.remove()
      if (mapInstance.current) mapInstance.current.remove()
    }
  }, [])

  /* ======================
     팝업 마커
  ====================== */
  useEffect(() => {
    if (!mapInstance.current) return

    // 기존 마커 제거
    markers.current.forEach(m => m.remove())
    markers.current = []

    popups.forEach(popup => {
      if (!popup.latlng) return

      const isSelected = selectedIds.includes(popup.id)

      const icon = window.L.divIcon({
        className: 'popup-marker',
        html: `<div style="
          background: ${isSelected ? '#3b82f6' : '#ef4444'};
          width: ${isSelected ? 20 : 16}px;
          height: ${isSelected ? 20 : 16}px;
          border-radius: 50%;
          border: 3px solid white;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        "></div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      })

      const marker = window.L.marker(popup.latlng, { icon })
        .addTo(mapInstance.current)
        .on('click', () => onSelect(popup.id))
        .bindPopup(`
          <div style="min-width:200px">
            <h4 style="margin:0 0 6px">${popup.name}</h4>
            <p style="margin:0;font-size:12px;color:#666">${popup.address}</p>
          </div>
        `)

      markers.current.push(marker)

      if (isSelected && popup.id === selectedIds[0]) {
        marker.openPopup()
        mapInstance.current.panTo(popup.latlng)
      }
    })

    if (markers.current.length) {
      const group = window.L.featureGroup(markers.current)
      mapInstance.current.fitBounds(group.getBounds(), {
        padding: [30, 30],
        maxZoom: 16,
      })
    }
  }, [popups, selectedIds, onSelect])

  /* ======================
     방문 경로 + 순서 (핵심)
  ====================== */
  useEffect(() => {
    if (!mapInstance.current || !routeData?.routeCoordinates) return

    // 기존 제거
    if (routeLayer.current) routeLayer.current.remove()
    orderMarkers.current.forEach(m => m.remove())
    orderMarkers.current = []

    // 🔥 방문 순서 = 배열 순서
    const pathCoords = routeData.routeCoordinates.slice(0, -1)

    // 경로
    routeLayer.current = window.L.polyline(pathCoords, {
      color: '#3b82f6',
      weight: 8,
      opacity: 0.9,
      dashArray: '14,8',
    }).addTo(mapInstance.current)

    // 방문 순서 번호
    pathCoords.forEach((coord, i) => {
      const orderIcon = window.L.divIcon({
        className: '',
        html: `
          <div style="
            width: 28px;
            height: 28px;
            background: #222;
            color: white;
            border-radius: 50%;
            border: 4px solid white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 13px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
          ">
            ${i + 1}
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      })

      const m = window.L.marker(coord, { icon: orderIcon })
        .addTo(mapInstance.current)

      orderMarkers.current.push(m)
    })

    setTimeout(() => {
      mapInstance.current.fitBounds(routeLayer.current.getBounds(), {
        padding: [50, 50],
      })
    }, 200)
  }, [routeData])

  return (
    <div
      ref={mapRef}
      style={{ width: '100%', height: '100%', minHeight: '500px' }}
    />
  )
}