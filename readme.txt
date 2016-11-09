목차
1. 소개
2. 설치전 확인 사항
3. 설치방법
4. 설정방법
5. 인수소개

1. 소개
 이 프로그램은 EPG(Electronic Program Guide)를 웹상의 여러 소스에서 가져와서 XML로 출력하는 프로그램으로 python2에서 사용 가능하도록 제작되었다.

2. 설치전 확인 사항
 이 파일을 사용하기 위해서는 몇가지 전제 조건이 있으므로 확인후 설치하도록 한다.
 * ALLCh.json 또는 IPTV별 json 파일을 열어보면 아래와 같은 내용으로 KTCh, SKCh, LGCh 항목을 확인할 수 있다.
   이 항목은 IPTV별 채널 번호로 tvheadend에 설정되어 있는 채널번호와 일치해야 한다.
   {"Id":1,"KTCh":163,"SKCh":215,"LGCh":null,"Name":"9colors","Source":"SK","ServiceId":285}
   
  * 파일을 실행하기 위해서는 별도의 python 모듈이 필요할 수 있으므로 설치가 필요할 수 있다.

3. 설치방법
  2.1 파일을 압축해제
  2.2 epg2xml.py의 # Set My Configuration 안의 부분을 4. 설정방법에 따라서 설정한다.
  2.3 설정이 끝나면 tvheadend의 서버의 적당한 곳에 파일을 올려놓는다.
  2.4 단독으로 실행가능하게 하려면 chmod +x epg2xml.py 명령어를 사용한다.
  2.5 tv_grab_file 사용시
      tv_grab_file 안의 cat xmltv.xml 또는 wget 부분을
      /파이썬설치경로/python /epg2xml.py 경로/epg2xml.py -d 또는
      /epg2xml.py 경로/epg2xml.py -d
  2.6 XMLTV 사용시
      /파이썬설치경로/python /epg2xml.py 경로/epg2xml.py -s xmltv.sock경로 또는
      /epg2xml.py 경로/epg2xml.py -s xmltv.sock 경로
      4. 설정방법에 defaul_xml_socket에 xmltv.sock의 경로를 설정하였다면
      /파이썬설치경로/python /epg2xml.py 경로/epg2xml.py -s 또는
      /epg2xml.py 경로/epg2xml.py -s
      XMLTV 사용시에는 크론에 실행할 시간을 등록해야 한다.

4. 설정방법
# Set My Configuratoin 안의 항목이 설정 가능한 항목이다.
  MyISP  : 사용하고 있는 IPTV 선택한다. KT, LG, SK 로 설정 가능하다.
  userid : tvheadend의 admin 아이디
  userpw : tvheadend의 admin 비밀번호
  host   : tvheadend의 내부 아이피
  port   : thveadend의 포트 번호
  ChDelimiter : HD 채널과 SD 채널과의 구분자 ex) -SD
  offset : SD 채널을 사용할 시 HD 채널과의 번호차 ex) 500
  icorurl : 채널별 아이콘이 있는 url을 설정할 수 있다. 아이콘의 이름은 json 파일에 있는 Id.png로 기본설정되어 있다.
  default_xml_filename : EPG 저장시 기본 저장 이름으로 tvheadend 서버가 쓰기가 가능한 경로로 설정해야 한다.
  default_xml_socket   : External XMLTV 사용시 xmltv.sock가 있는 경로로 설정해준다.

5. 인수소개
실행시 사용가능한 인수는 현재 총 4가지가 있으며 --help 명령어로 4가지 인수를 볼 수 있다.
  --version : 버전을 보여준다.
  -d --display : EPG 정보를 화면으로 보여준다. 
  -o --outfile : EPG 정보를 파일로 저장한다. ex) -o xmltv.xml
  -s --socket  : EPG 정보를 xmltv.sock로 전송한다. ex) -s /var/run/xmltv.sock