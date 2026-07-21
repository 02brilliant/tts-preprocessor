# Retired implementation archive

이 디렉터리는 지원 종료된 과거 비교·레거시 구현의 일시 보관소다.

- current production runtime에서 사용하지 않는다.
- current tests에서 사용하지 않는다.
- build, package, release, deployment에 포함하지 않는다.
- canonical policy의 일부가 아니다.
- 이 디렉터리의 파일은 복구 또는 fallback 기준이 아니다.
- 이 디렉터리를 전체 삭제해도 current project behavior가 달라지지 않아야 한다.
- 향후 별도 승인 없이 current source로 다시 연결하지 않는다.

이 디렉터리는 Python package가 아니다. 보관된 Python source와 test는
`.retired` 확장자를 사용하며 실행·import·pytest 수집 대상이 아니다.
