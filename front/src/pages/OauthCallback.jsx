import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

export default function OauthCallback() {
  const navigate = useNavigate()
  const { search } = useLocation()

  useEffect(() => {
    const params = new URLSearchParams(search)
    const code = params.get('code')

    if (!code) {
      alert('로그인 실패')
      navigate('/')
      return
    }

    ;(async () => {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/auth/kakao/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      const data = await res.json()

      if (res.ok) {
        localStorage.setItem('access', data.access)
        localStorage.setItem('refresh', data.refresh)
        localStorage.setItem('user', JSON.stringify(data.user))
        alert(`환영합니다 ${data.user.nickname}님`)
        navigate('/')
      } else {
        alert('로그인 처리 실패')
      }
    })()
  }, [search])

  return <div>로그인 처리중...</div>
}