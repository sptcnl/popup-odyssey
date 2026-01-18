const API_BASE = 'http://localhost:8000/api';

export const storesApi = {
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