# Apice.kr

실험 관리 시스템

해당 리포지토리는 실제 운영 중인 서비스의 소스코드이며, 서비스 주소는 [www.apice.kr](https://www.apice.kr)입니다.<br><br>

이 프로젝트는 학교 내 실험 활동을 보다 명확한 절차로 관리하기 위해 만들었습니다.<br>
실험 계획서 제출, 참여자 모집, 승인 여부 확인 과정을 하나의 시스템으로 통합하여 관리자와 학생 모두가 현재 상태를 쉽게 확인할 수 있도록 구성했습니다.<br><br>

> 당시 급하게 필요한 상황이라 Flask로 빠르게 구현했습니다.<br>
> Express.js에 비해 유지보수 측면에서 아쉬운 점이 있을 수 있다는 점을 감안하고 개발했습니다.
>
> 이 리포지토리는 [LICENSE](https://github.com/Anion15/Apice.kr/blob/main/LICENSE)로 보호됩니다.<br>
> 사용, 복사, 수정, 배포, 서브라이선스 관련 문의는 `juwony27@gmail.com`으로 부탁드립니다.

## Project Structure

```bash
Apice.kr/
├── app.py
├── requirements.txt
├── templates/
└── README.md
```


## Database Schema

### experiments

- `id`: 실험 고유 ID
- `title`: 실험 제목
- `description`: 실험 설명
- `max_participants`: 모집 인원
- `created_by`: 작성자 이름
- `created_at`: 작성 일시
- `approved`: 승인 여부 (`0`: 대기, `1`: 승인됨)
- `approved_by`: 승인자 이름
- `approved_at`: 승인 일시

### participants

- `id`: 참여 신청 고유 ID
- `experiment_id`: 실험 ID
- `name`: 참여자 이름
- `email`: 참여자 이메일
- `status`: 상태 (`pending`, `approved`, `rejected`)
- `applied_at`: 신청 일시
- `approved_at`: 승인 일시

## API Endpoints

### Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | 메인 페이지 |
| GET | `/regist` | 실험 계획서 작성 페이지 |
| POST | `/regist` | 실험 계획서 제출 |
| GET | `/join` | 실험 참여 신청 페이지 |
| POST | `/api/apply` | 실험 참여 신청 |
| GET | `/api/experiments` | 승인된 실험 목록 조회 |
| GET | `/api/experiments/<id>` | 실험 상세 조회 |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin` | 관리자 페이지 |
| GET | `/api/admin/pending-experiments` | 승인 대기 실험 목록 조회 |
| GET | `/api/admin/pending-participants` | 승인 대기 참여자 목록 조회 |
| POST | `/api/admin/approve-experiment/<id>` | 실험 승인 |
| POST | `/api/admin/reject-experiment/<id>` | 실험 거절 |
| POST | `/api/admin/approve-participant/<id>` | 참여자 승인 |
| POST | `/api/admin/reject-participant/<id>` | 참여자 거절 |


----
<br><br>
### 여담

현재 이 프로젝트는 집에서 직접 운영 중인 리눅스 서버에서 돌아가고 있습니다.  
그래서 서버 자원과 유지 부담을 고려해, [실험계획서 작성](https://github.com/Anion15/Apice.kr/blob/main/templates/register_experiment.html) 페이지에는 파일 업로드 기능을 별도로 넣지 않았습니다.

<br>

<p align="center">
  <sub>
    Apice.kr · 실험 관리 시스템
  </sub>
</p>

