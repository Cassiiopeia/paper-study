📝 현재 문제점
---

- 이 저장소는 논문 튜터 저장소로 시작해 이슈, 릴리스, 버전 관리 체계가 없다.
- 레포 자체를 고치는 작업(규칙, 스크립트, 노트 틀)이 이슈 없이 곧바로 커밋돼 무엇을 왜 바꿨는지 추적하기 어렵다.

🛠️ 해결 방안 / 제안 기능
---

- project-auto-wizard를 basic 타입으로 설치해 GitHub 네이티브 릴리스 자동화 파이프라인을 도입한다.
- 개발 브랜치는 develop, 릴리스 브랜치는 main. 배포 대상 서버가 없으므로 서버 배포, Nexus publish, Secret 백업 워크플로우는 제외한다.
- 앞으로 레포 개선 작업은 "이슈 생성 → 구현 → 커밋 → 배포" 순서를 따른다. 논문 읽기 세션 기록은 기존대로 바로 커밋한다.

⚙️ 작업 내용
---

- project-auto-wizard basic 설치 (develop → main, 배포/Nexus/Secret 백업 제외)
- 생성물 확인: `.github/workflows/` 공통 워크플로우 6개, `.github/scripts/` 헬퍼 4개, `version.yml`(0.0.1), `README.md` 버전 섹션
- 이슈 라벨(작업전, 작업중, 작업완료) 정비
- develop 브랜치 생성 및 첫 커밋

🙋‍♂️ 담당자
---

- 전체: Cassiiopeia
