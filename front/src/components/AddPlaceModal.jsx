import { useState } from 'react'
import { storesApi } from '../api/stores'

export default function AddPlaceModal({ onClose }) {
  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [isPopup, setIsPopup] = useState(false)
  const [isPublic, setIsPublic] = useState(true)
  const [isLoading, setIsLoading] = useState(false)

  // 팝업 체크 시 자동 공개
  const handleIsPopupChange = (e) => {
    setIsPopup(e.target.checked)
    if (e.target.checked) setIsPublic(true)
  }

  const handleSubmit = async () => {
    if (!name || !address) {
      alert('이름과 주소를 입력해주세요')
      return
    }
    if (isPopup && (!startDate || !endDate)) {
      alert('팝업은 시작일과 종료일을 입력해주세요')
      return
    }

    try {
      setIsLoading(true)
      await storesApi.createPlace({
        name, 
        address,
        isPopup: isPopup,
        start_date: startDate,
        end_date: endDate,
        is_public: isPublic
      })
      alert('장소가 등록되었습니다!')
      onClose()
    } catch (error) {
      console.error(error)
      alert('등록 실패: ' + (error.message || '알 수 없는 오류'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <h3>🆕 장소 추가</h3>

        <input
          placeholder="장소 이름 *"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={input}
        />

        <input
          placeholder="주소 * (예: 서울 성동구 성수동2가 284)"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          style={input}
        />

        {!isPopup && (
          <label style={checkboxLabel}>
            <input 
              type="checkbox" 
              checked={isPublic} 
              onChange={(e) => setIsPublic(e.target.checked)} 
              style={checkbox} 
            />
            공개하기 (체크 해제 시 나만 보기)
          </label>
        )}

        <label style={checkboxLabel}>
          <input 
            type="checkbox" 
            checked={isPopup} 
            onChange={handleIsPopupChange} 
            style={checkbox} 
          />
          팝업스토어 <span style={infoText}>(날짜 입력 필요)</span>
        </label>

        {isPopup && (
          <>
            <label style={dateLabel}>시작일 *</label>
            <input 
              type="date" 
              value={startDate} 
              onChange={(e) => setStartDate(e.target.value)} 
              style={input} 
            />
            <label style={dateLabel}>종료일 *</label>
            <input 
              type="date" 
              value={endDate} 
              onChange={(e) => setEndDate(e.target.value)} 
              style={input} 
            />
          </>
        )}

        <div style={buttonContainer}>
          <button 
            onClick={handleSubmit} 
            disabled={isLoading}
            style={{...primaryBtn, ...(isLoading && {opacity: 0.7, cursor: 'not-allowed'})}}
          >
            {isLoading ? '등록 중...' : '등록하기'}
          </button>
          <button 
            onClick={onClose} 
            disabled={isLoading}
            style={subBtn}
          >
            취소
          </button>
        </div>
      </div>
    </div>
  )
}

const overlayStyle = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 3000
}

const modalStyle = {
  background: 'white', padding: '24px', borderRadius: '12px', width: '340px',
  maxHeight: '90vh', overflowY: 'auto', display: 'flex', flexDirection: 'column',
  gap: '12px', boxShadow: '0 20px 40px rgba(0,0,0,0.15)'
}

const input = {
  padding: '12px', fontSize: '14px', borderRadius: '8px', border: '1px solid #ddd',
  outline: 'none', transition: 'border-color 0.2s'
}

const dateLabel = { fontSize: 12, color: '#666', marginBottom: 4 }

const primaryBtn = {
  flex: 1, background: '#228be6', color: 'white', border: 'none',
  padding: '12px', borderRadius: '8px', cursor: 'pointer', fontWeight: 500
}

const subBtn = {
  flex: 1, background: '#e9ecef', color: '#495057', border: 'none',
  padding: '12px', borderRadius: '8px', cursor: 'pointer', fontWeight: 500
}

const buttonContainer = { display: 'flex', gap: '8px', marginTop: '8px' }

const checkboxLabel = {
  display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px',
  cursor: 'pointer', userSelect: 'none', padding: '8px 0'
}

const checkbox = { width: '16px', height: '16px', accentColor: '#228be6' }

const infoText = { fontSize: '12px', color: '#666', fontWeight: 'normal' }