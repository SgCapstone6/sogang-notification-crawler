from urllib.request import urlopen, Request
from urllib.parse import urlencode
from chardet import detect
from bs4 import BeautifulSoup
from collections import namedtuple
from datetime import datetime, timedelta


#######################       Temporary Code for session         ################################
# Please enter your sogang id & password
userid = ''
passwd = ''
#################################################################################################



#tag_info: namedtuple which stores tag information
#it has 4 values (tag_name, attr_name, attr_value, idx)
tag_info = namedtuple('tag_info','tag_name attr_name attr_value idx')

#crawler_info: namedtuple which stores crawler information
#it has 4 values (wrap_tag, title_tag, time_tag, trim_str)
crawler_info = namedtuple('crawler_info','wrap_tag title_tag time_tag trim_str')

#site_info : namedtuple which stores site informations
#it has 6 values (site_id, url_L, crawler_L, time_parser_L, url_flag, session)
site_info = namedtuple('site_info','site_id url_L crawler_L time_parser_L url_flag session')

#crawling_info: namedtuple which stores result of crawling
#It has 5 values (site_id, year, month, day, title, url)
#site_id (int), year (int), month (int), day (int), title (str), url (str)
crawling_info = namedtuple('crawling_result','site_id year month day title url')


#starting from the location where start string appears, trim the text to the end string
def trim_html(source, start_str,end_str):
    if start_str != None :
        ret = source[source.find(start_str):]
    if end_str != None :
        ret = ret[:ret.find(end_str)]
    return ret

#find all soups which satisfies tag information. It support recursive finding.
def find_by_tag_info(soup,tag_list):
    L = [soup]
    for tag in tag_list:
        next_L = []
        slicing = tag.idx.split(':')
        for s in L:
            temp_L = s.find_all(tag.tag_name, {tag.attr_name:tag.attr_value})
            if len(slicing) == 1:
                next_L.append(temp_L[int(slicing[0])])
            else:
                if slicing[0] == '':
                    s_idx = 0
                else: s_idx = int(slicing[0])
                if slicing[1] == '':
                    e_idx = len(temp_L)
                else : e_idx = int(slicing[1])
                inc = 1
                if len(slicing) == 3:
                    if slicing[2] != '': inc = int(slicing[2])
                next_L.extend(temp_L[s_idx:e_idx:inc])
        L = next_L
    return L

def make_cookie():
    global userid
    global passwd
    login_url='https://job.sogang.ac.kr/ajax/common/loginproc.aspx'
    login_data = {'userid' : userid,'passwd' : passwd}
    login_req = urlencode(login_data).encode('utf-8')
    request = Request(login_url,login_req)
    f=urlopen(request)
    cookies = f.headers.get_all('Set-Cookie')
    cookie = ';'.join(cookies)
    return cookie

def notice_crawling(site, depth):
    #Initialization
    notice_url = site.url_L[depth]
    default_dt = datetime.strptime('','')
    session = site.session
    site_id = site.site_id
    idx = 1
    ret = []
    crawler = site.crawler_L[depth]
    time_parser = site.time_parser_L[depth]
    url_flag = site.url_flag

    #Request HTML text
    
    if session == True:
        cookie = Cookie.make_cookie()
        request = Request(notice_url)
        request.add_header('cookie',cookie)
        response = urlopen(request)
        html = response.read()
    else:        
        html = urlopen(notice_url).read()

    #Encoding HTML text
    chdt = detect(html)
    html = html.decode(chdt['encoding'])
    #Trim HTML and replace '\r'
    html = html.replace('\r','')
    #html = html.replace('&curren','&ampCurren') # and curren symbol replace
    if crawler.trim_str != None:
        html =trim_html(html,*(crawler.trim_str))

    #Parse html and make a bs4 class
    soup = BeautifulSoup(html,'html.parser')


    #Crawling wrap tag
    if crawler.wrap_tag != None:
        L = find_by_tag_info(soup , crawler.wrap_tag)
    else :
        L = [soup]

    for wrapper in L:
        #initialization
        year,month,day = default_dt.year, default_dt.month, default_dt.day #default time 1900.01.01
        title_text = None; content_url = None

        #Title Crawling
        if crawler.title_tag != None :
            title_soup = find_by_tag_info(wrapper, crawler.title_tag) # url_wrapper which contains url tag
            title_text_L = [soup.text.strip() for soup in title_soup] 
            title_text = '/'.join(title_text_L)
    
            if title_text.find('\n')>=0: #title exception
                title_text = title_text[title_text.find('\n')+1 :]

        #Time Crawling
        if crawler.time_tag != None and time_parser != None :
            time_text = find_by_tag_info(wrapper,crawler.time_tag)[0].text.strip()
            time = datetime.strptime(time_text,time_parser) #extract time infromation by using time expression
            year,month,day = time.year, time.month, time.day

        #URL Crawling
        if url_flag[depth] == True:
            content_url = wrapper.find('a')['href']
            if content_url[0:4] != 'http':
                if content_url[0] == '/':
                    content_url = "/".join(notice_url.split('/')[0:3]) + content_url
                else :
                    content_url = notice_url[:notice_url.rfind('/')+1] + content_url
                    
        #Recursive Crawling of notice URL
        if depth < len(site.crawler_L) - 1 :
            site.url_L[depth+1]=content_url
            crawled = notice_crawling(site,depth+1)[0]
            if crawled.title != None :  #Overwrite title
                title_text = crawled.title
            if crawled.url != None:     #Overwrite url
                content_url = crawled.url

            #Merge time NOT overwrite
            if year == default_dt.year : year = crawled.year
            if month == default_dt.month : month = crawled.month
            if day == default_dt.day : day = crawled.day 
                
        idx +=1
        ret.append(crawling_info(site_id,year,month,day,title_text,content_url))
    return ret

def trim_by_time(crawled_L, time_term):
    now  = datetime.now()
    ret = []
    for crawled in crawled_L:
        post_time = datetime(crawled.year, crawled.month, crawled.day)
        if time_term >= now - post_time:
            ret.append(crawled)
    return ret

#Print crawling info of site
def print_crawling_info(crawled_L):
    idx = 1
    for crawled in crawled_L:
        print('###',idx)
        print('SITE  :',crawled.site_id)
        print('TITLE :',crawled.title)
        print('TIME  :',crawled.year,crawled.month,crawled.day)
        print('URL   :',crawled.url)
        idx += 1

#Jobevent crawler is a function to crawl only jobevent notices in jobsogang page
def jobevent_crawler():
    notice_url = 'https://job.sogang.ac.kr/jobevent/list.aspx'
    wrap_tag = [tag_info('tr',None,None,':')]
    title_tag1 = [tag_info('td',None,None,'1:3')]
    title_tag2 = [tag_info('td',None,None,'4')]
    trim_str = ('<tbody>','</tbody>')
    time_tag = None
    crawler1 = crawler_info(wrap_tag,title_tag1,None,trim_str)
    crawler2 = crawler_info(wrap_tag,title_tag2,None,trim_str)
    site1 = site_info([notice_url],[crawler1],[None],[True], True)
    site2 = site_info([notice_url],[crawler2],[None],[False], True)
    crawled1 = notice_crawling(site1,0)
    crawled2 = notice_crawling(site2,0)

    now_dt = datetime.now()
    ret_L = []
    for i in range(len(crawled2)):
        if crawled2[i].title != '-':
            ret_L.append(crawling_info(now_dt.year,now_dt.month,now_dt.day\
                                    ,crawled1[i].title,\
                                    crawled1[i].url))
    return ret_L

####################################    DB part  start  ##########################################

crawler_L = [None] * 28
time_parser_L = [None]* 12

site_data_L = [['1','http://kyomok.sogang.ac.kr/front/cmsboardlist.do?siteId=kyomok&bbsConfigFK=1101',\
                '1','1','TRUE','FALSE']]
crawler_data_L = [['1','li,None,None,:','a,class,title,0','div,None,None,0/span,None,None,1',\
                    '<!-- 상단고정 시작 -->,<!-- List 끝 -->']]
time_parser_data_L = [['1','%Y.%m.%d']]

for crawler_data in crawler_data_L:
    crawler_id = int(crawler_data[0])
    tag_L = [None,None,None]
    for i in range(1,4):
        if crawler_data[i] == 'None':
            continue
        tag_L[i-1] = []
        for tag_data in crawler_data[i].split('/'):
            tag_param = []
            for tag_str in tag_data.split(','):
                if tag_str == 'None':
                    tag_param.append(None)
                else: tag_param.append(tag_str)
            tag_L[i-1].append(tag_info(*tag_param))
    if crawler_data[4] == 'None':
        trim_str = None
    else: trim_str = tuple(crawler_data[4].split(','))
    crawler_L[crawler_id] = crawler_info(tag_L[0],tag_L[1],tag_L[2],trim_str)

for time_parser_data in time_parser_data_L:
    time_parser_id = int(time_parser_data[0])
    time_re = time_parser_data[1]
    time_parser_L[time_parser_id] = time_re

for site_data in site_data_L:
    site_id = int(site_data[0])
    notice_url_param = [site_data[1]]
    crawler_idx_L = site_data[2].split(',')
    time_parser_idx_L = site_data[3].split(',')
    
    url_flag_param = [flag.lower() == 'true' for flag in site_data[4].split(',')]
    notice_url_param += [None] * (len(crawler_idx_L) -1)

    if 10 <= site_id <= 16: #job sogang crawling
        session = True
    else: session = False

    crawler_param = []
    time_parser_param = []
    for i in range(len(crawler_idx_L)):
        crawler_param.append(crawler_L[int(crawler_idx_L[i])])
        if time_parser_idx_L[i] == 'None':
            time_parser_param.append(None)
        else:
            time_parser_param.append(time_parser_L[int(time_parser_idx_L[i])])
    site = site_info(site_id,notice_url_param,crawler_param,time_parser_param,url_flag_param,session)
    crawled_L = notice_crawling(site,0)
    time_term = timedelta(days=4) #time_term = 1 day
    crawled_L = trim_by_time(crawled_L,time_term)
    print_crawling_info(crawled_L)
    
#site_id = 1
#notice_url = ['http://kyomok.sogang.ac.kr/front/cmsboardlist.do?siteId=kyomok&bbsConfigFK=1101']

#Crawler : It's possible to exist many crawlers. so variable 'crawler' is a list []
#wrap_tag = [tag_info('li',None,None,':')] #crawler number 1
#title_tag = [tag_info('a','class','title','0')] #crawler number 1
#time_tag = [tag_info('div',None,None,'0'),tag_info('span',None,None,'1')] #crawler number 1
#trim_str = ('<!-- 상단고정 시작 -->','<!-- List 끝 -->') #crawler number 1
#crawler = [crawler_info(wrap_tag,title_tag,time_tag,trim_str)]

#time_parser : It's possible to exist many time parsers. so variable 'time_parser' is a list []
#time_parser = ['%Y.%m.%d']

#URL flag : It's possible to exist URL flags. so variable 'url_flag' is a list []
#url_flag = [True]

#session
#session = False

#Make site namedtuple by using (site_id, crawler,time_parser, url_flag, session) 
#site = site_info(site_id, notice_url,crawler,time_parser,url_flag, session)

####################################    DB part  end  ############################################


# test and print crawling results
#print_crawling_info(notice_crawling(site,0))
#print_crawling_info(jobevent_crawler()) # It's only used when we crawls job event in job sogang.
