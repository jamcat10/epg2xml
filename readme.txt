목차
0. 버전
1. 소개
2. 설치전 확인 사항
3. 설치방법
4. 설정방법
5. 인수소개
6. 변경사항
7. 개선사항
8. 알려진 버그

0. 버전
 1.0.6
1. 소개
 이 프로그램은 EPG(Electronic Program Guide)를 웹상의 여러 소스에서 가져와서 XML로 출력하는 프로그램으로 python2에서 사용 가능하도록 제작되었다.

2. 설치전 확인 사항
 BeautifulSoup(b4), lxml 모듈이 추가로 필요하다.
 설치 OS별로 모듈을 설치하기 위한 사전 설치 방법이 다를 수도 있으므로 검색해서 설치하도록 한다.
 synology의 경우 파이썬 모듈을 설치하면  easy_install beautifulsou, easy_install lxml 이다

3. 설치방법
 파일 압축 해제후 원하는 경로에 넣는다.
 3.1 tv_grab_file 사용시
    tv_grab_file 안의 cat xmltv.xml 또는 wget 부분을
    /파이썬설치경로/python /epg2xml.py 경로/epg2xml.py -i KT(SK, LG) -d 또는
    /epg2xml.py 경로/epg2xml.py -i KG(SK, LG) -d
 3.2 XMLTV 사용시
    /파이썬설치경로/python /epg2xml.py 경로/epg2xml.py -i KT(SK, LG) -s xmltv.sock경로 또는
    /epg2xml.py 경로/epg2xml.py -i KT(SK, LG) -s xmltv.sock 경로
 
 - XMLTV 사용시에는 크론에 실행할 시간을 등록해야 한다.

4. 설정방법
 # Set My Configuratoin 안의 항목이 설정 가능한 항목이다. 인수로 처리하지 않고 이 부분을 수정해서 사용할 수도 있지만,
   이 부분을 직접 수정하는 것보다는 향후 업그레이드시 변경될 수 있으므로 인수로 처리하기를 권장한다.

  default_icon_url : 채널별 아이콘이 있는 url을 설정할 수 있다. 아이콘의 이름은 json 파일에 있는 Id.png로 기본설정되어 있다.
  default_fetch_limit : EPG 데이터 가져오는 기간이다.
  default_xml_filename : EPG 저장시 기본 저장 이름으로 tvheadend 서버가 쓰기가 가능한 경로로 설정해야 한다.
  default_xml_socket   : External XMLTV 사용시 xmltv.sock가 있는 경로로 설정해준다.

 Channel.json 파일을 텍스트 편집기로 열어보면 각채널별 정보가 들어 있다.
 이중 Enabled:1로 되어 있는 부분을 Enabled:0으로 바꾸면 EPG정보를 가져오지 않는다.
 필요없는 채널정보를 가져오지 않게 하는 것으로 EPG 정보 수집시 시간을 단축할 수 있다.

5. 인수소개
실행시 사용가능한 인수는 --help 명령어로 확인이 가능하다
  -h --help : 도움말 출력
  --version : 버전을 보여준다.
  -i : IPTV 선택 (KT, SK, LG 선택가능) ex) -i KT
  -d --display : EPG 정보를 화면으로 보여준다. 
  -o --outfile : EPG 정보를 파일로 저장한다. ex) -o xmltv.xml
  -s --socket  : EPG 정보를 xmltv.sock로 전송한다. ex) -s /var/run/xmltv.sock
  -l --limit : EPG 정보 가져올 기간으로 기본값은 2일이며 최대 7일까지 설정 가능하다. ex) -l 2
  --icon : 채널 icon 위치 URL ex) --icon http://www.example.com

6. 변경사항
 - urllib를 urllib2로 변경
 - User Agent 추가
 - 누락된 LG 채널 추가
 - 채널 소스 변경

 7. 개선사항
  - 코드 최적화
  - 속도 개선
  - 등급 아이콘 추가
  - 채널 json 편집기 추가

8. 알려진 버그
  - KT, LG를 소스로 하는 채널의 EPG정보는 가져오는 기간의 제일 마지막 방송정보를 표시하지 않음
