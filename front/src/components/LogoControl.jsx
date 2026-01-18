import { useEffect } from 'react'

export default function LogoControl({ mapInstance }) {
  useEffect(() => {
    if (!mapInstance.current || !window.L) return

    const timeoutId = setTimeout(() => {
      const LogoControl = window.L.Control.extend({
        options: { position: 'topleft' },
        onAdd: function() {
          const div = window.L.DomUtil.create('div', 'logo-control')
          div.innerHTML = `
            <div style="
              width: 130px; height: 40px;
              background: linear-gradient(135deg, #ff6b6b, #4ecdc4);
              border-radius: 12px;
              display: flex; align-items: center; justify-content: center;
              color: white; font-weight: bold; font-size: 12px;
              box-shadow: 0 8px 32px rgba(0,0,0,0.3);
              margin: 8px 0 0 8px;  /* 🎯 더 위로! 더 왼쪽으로! */
            ">
              🏪 팝업순례
            </div>
          `
          window.L.DomEvent.disableClickPropagation(div)
          return div
        }
      })

      const control = new LogoControl()
      control.addTo(mapInstance.current)
      
      return () => control.remove()
    }, 200)

    return () => clearTimeout(timeoutId)
  }, [mapInstance])

  return null
}