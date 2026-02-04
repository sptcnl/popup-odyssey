import { authFetch } from './authFetch';

const API_BASE = import.meta.env.VITE_API_BASE;

export const storesApi = {
  async createPlace({ name, address, is_popup, start_date, end_date, is_public = true }) {
    console.log('Place 생성 API 호출:', { name, address, is_popup, start_date, end_date, is_public });
    
    const response = await authFetch(`${API_BASE}/places/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access')}`
      },
      body: JSON.stringify({ 
        name, 
        address, 
        is_public,
        is_popup,
        ...(is_popup && { start_date, end_date })
      }),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Place 생성 실패:', errorText);
      throw new Error(`장소 등록 실패: ${response.status}`);
    }
    
    return response.json();
  },

  async getPlaces() {
    const headers = {
      'Content-Type': 'application/json',
    };

    const token = localStorage.getItem('access')

    // 🔥 토큰이 있을 때만 Authorization 추가
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await authFetch(`${API_BASE}/places/`, { 
      headers,
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`장소 로드 실패 (${response.status}): ${errorText}`);
    }

    return await response.json();
  },

  async optimizeRoute({ coordinates }) {
    console.log('API 호출:', { coordinates })
    
    const response = await authFetch(`${API_BASE}/routes/compute/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ coordinates }),
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('서버 에러 응답:', errorText)
      throw new Error(`경로 최적화 실패: ${response.status} ${errorText}`)
    }
    return response.json()
  }
};