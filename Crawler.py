from urllib.request import urlopen
import chardet
import re
from bs4 import BeautifulSoup
from collections import namedtuple
from datetime import datetime

#trim_str is tuple of string (start_str, end_str)

#Namedtuple
crawler_info = namedtuple('crawler_info','wrap_tag title_tag time_tag time_re trim_str url_flag')
tag_info = namedtuple('tag_info','tag_name attr_name attr_value idx')
crawling_info = namedtuple('crawling_result','year month day title url')

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

def notice_crawling(notice_url,crawler_L):
    html = urlopen(notice_url).read()
    chdt = chardet.detect(html)
    html = html.decode(chdt['encoding'])
    crawler = crawler_L[0]
    html = html.replace('\r','')
    default_dt = datetime.strptime('','')
    #html = html.replace('&curren','&ampCurren') # and curren symbol replace
    if crawler.trim_str != None:
        html =trim_html(html,*(crawler.trim_str))
    
    soup = BeautifulSoup(html,'html.parser')

    if crawler.wrap_tag != None:
        L = find_by_tag_info(soup , crawler.wrap_tag)
    else : #whole html
        L = [soup]
    idx = 1
    ret = []
    for wrapper in L:
        #initializing
        year,month,day = default_dt.year, default_dt.month, default_dt.day
        title_text = None; content_url = None
        
        if crawler.title_tag != None :
            title_soup = find_by_tag_info(wrapper, crawler.title_tag) # url_wrapper which contains url tag
            title_text = title_soup[0].text.strip()
            
            if title_text.find('\n')>=0: #title exception
                title_text = title_text[title_text.find('\n')+1 :]

        if crawler.time_tag != None and crawler.time_re != None :
            time_text = find_by_tag_info(wrapper,crawler.time_tag)[0].text.strip()
            time = datetime.strptime(time_text, crawler.time_re) #extract time infromation by using time expression
            year,month,day = time.year, time.month, time.day

        if crawler.url_flag == True :
            content_url = wrapper.find('a')['href']
            if content_url[0:4] != 'http':
                if content_url[0] == '/':
                    content_url = "/".join(notice_url.split('/')[0:3]) + content_url
                else :
                    content_url = notice_url[:notice_url.rfind('/')+1] + content_url

            if len(crawler_L) > 1 : #title, time can be extracted by using url (ex : when title or time are omitted)
                crawled = notice_crawling(content_url, crawler_L[1:])[0]
                if crawled.title != None :
                    title_text = crawled.title
                if crawled.url != None:
                    content_url = crawled.url
                if year == default_dt.year : year = crawled.year
                if month == default_dt.month : month = crawled.month
                if day == default_dt.day : day = crawled.day 
                
        # if url attribute is None, we can't extract url link

            
        idx +=1
        ret.append(crawling_info(year,month,day,title_text,content_url))
    return ret

def print_crawling_info(crawled_L):
    idx = 1
    for crawled in crawled_L:
        print('###',idx)
        print('TITLE :',crawled.title)
        print('TIME  :',crawled.year,crawled.month,crawled.day)
        print('URL   :',crawled.url)
        idx += 1

notice_url = 'http://kyomok.sogang.ac.kr/front/cmsboardlist.do?siteId=kyomok&bbsConfigFK=1101'
wrap_tag = [tag_info('li',None,None,':')]
title_tag = [tag_info('a','class','title','0')]
time_tag = [tag_info('div',None,None,'0'),tag_info('span',None,None,'1')]
time_re = '%Y.%m.%d'
trim_str = ('<!-- 상단고정 시작 -->','<!-- List 끝 -->')
url_flag = True
crawler = crawler_info(wrap_tag,title_tag,time_tag,time_re,trim_str,url_flag)

wrap_tag = [tag_info('article',None,None,'0')]
title_tag = None
time_tag = [tag_info('strong',None,None,'1')]
time_re = '%y-%m-%d %H:%M'

trim_str = None
url_flag = False
t_crawler = crawler_info(wrap_tag,title_tag,time_tag,time_re,trim_str,url_flag)

print_crawling_info(notice_crawling(notice_url,[crawler]))
