const API_BASE = 'http://localhost:8000/api';

export const storesApi = {
  async createPlace({ name, address, is_popup, start_date, end_date, is_public = true }) {
    console.log('Place 생성 API 호출:', { name, address, is_popup, start_date, end_date, is_public });
    
    const response = await fetch(`${API_BASE}/places/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access')}`
      },
      body: JSON.stringify({ 
        name, 
        address, 
        is_public,
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
    const response = await fetch(`${API_BASE}/places/`);
    if (!response.ok) throw new Error('장소 목록 로드 실패');
    const data = await response.json();
    console.log(data)
    return data;
  },

  async optimizeRoute({ coordinates }) {
    console.log('API 호출:', { coordinates })
    
    const response = await fetch(`${API_BASE}/routes/compute/`, {
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