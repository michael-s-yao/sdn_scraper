import requests
from bs4 import BeautifulSoup
import re

class SDNScraper:
    # If the only punctuation there is is a question mark, then no helpful
    # information was provided.
    EXCLUDE = ['?']
    PUNCTUATION = ['.', '!']

    # Keywords for common queries.
    KEYWORDS_SECONDARY = ['secondary']
    KEYWORDS_INVITE = ['ii', 'interview invite', 'invite']
    KEYWORDS_DECISION = ['a.', 'a!', 'w.', 'w!', 'r.', 'r!', 'accept', 'waitlist', 'reject']
    KEYWORDS_FIN_AID = ['aid', 'finaid', 'fin aid', 'financial aid']

    # URLs for School Lists
    URLS = { '2021-2022': 'https://forums.studentdoctor.net/threads/2021-2022-alphabetical-listing-of-schools.1440875/',
             '2020-2021': 'https://forums.studentdoctor.net/threads/2020-2021-alphabetical-listing-of-schools.1406109/',
             '2019-2020': 'https://forums.studentdoctor.net/threads/2019-2020-alphabetical-listing-of-schools.1374208/',
             '2018-2019': 'https://forums.studentdoctor.net/threads/2018-2019-all-school-discussions-alphabetical-list.1350681/'}

    def __init__(self, data):
        # Get the desired page.
        self.page = requests.get(SDNScraper.URLS[data['year']])

        print(data)

        # Generate list of schools.
        soup = BeautifulSoup(self.page.content, 'html.parser')
        results = soup.find("div", class_="bbWrapper")
        school_sites = results.find_all("a", class_="link link--internal")
        school_names_urls = {}
        for site in school_sites:
            school_names_urls[site.text[10:]] = site['href']

        # Get requested school query.
        if not data['school_list']:
            schools_req = None
        else:
            schools_req = data['school_list'].split(',')
            if len(schools_req) == 1:
                schools_req = data['school_list'].split(' ')
            for i in range(len(schools_req)):
                # Remove extra spaces from beginning of school name.
                while schools_req[i][0] == ' ':
                    schools_req[i] == schools_req[i][1:]
                # Remove extra spaces from end of school name.
                while schools_req[i][-1] == ' ':
                    schools_req[i] == schools_req[i][:-1]
                if len(schools_req[i]) == 0:
                    schools_req[i] == None
                else:
                    # Convert school name to lower case.
                    schools_req[i] == schools_req[i].lower()

        # Get the school(s) to search for
        self.school_query = SDNScraper.guess_school(school_names_urls.keys(),
                                                    query=schools_req)
        urls = []
        for site in school_names_urls.keys():
            if site in self.school_query:
                urls.append(school_names_urls[site])
        self.urls = urls

        # Get the type of data to return.
        self.recency = (data['recency'] if data['recency'] is not None
                            else 'most recent')

        # Get the keyword to search for
        self.keyword = data['keyword'].lower()
        if self.keyword == 'other':
            self.keyword = data['opt-keyword'].lower()
            assert self.keyword is not None
            assert len(self.keyword) > 0
            self.keyword = [self.keyword]
        elif self.keyword == 'secondaries':
            self.keyword = SDNScraper.KEYWORDS_SECONDARY
        elif self.keyword == 'interviews':
            self.keyword = SDNScraper.KEYWORDS_INVITE
        elif self.keyword == 'decisions':
            self.keyword = SDNScraper.KEYWORDS_DECISION
        elif self.keyword == 'financial':
            self.keyword = SDNScraper.KEYWORDS_FIN_AID
        else:
            raise ValueError('Unrecognized Keyword!')

    def scrape(self):
        content = []
        # Parse through every school in the query list
        for i in range(len(self.urls)):
            # Parse through every page on the school-specific page
            school_url = self.urls[i]
            # Send preliminary page request to determine number of pages
            init_school_page = requests.get(school_url)
            init_school_soup = BeautifulSoup(init_school_page.content, 'html.parser')
            school_navigation = init_school_soup.find("ul", class_="pageNav-main")
            # Handle the case where only one page for the school
            if school_navigation is None: nav_sites=["-1"]
            # Handle the general case of multiple pages for the school
            else: nav_sites = school_navigation.find_all("li")

            ret_page = -1
            message_content = ""
            found = {}

            page_nums = range(1, len(nav_sites) + 1)
            if self.recency == 'most recent':
                page_nums = reversed(page_nums)
            for page_num in page_nums:
                # Send page request
                school_page = requests.get(school_url + "page-" + str(page_num))
                school_soup = BeautifulSoup(school_page.content, 'html.parser')
                # Retrieve the messages on the page
                school_messages = school_soup.find_all("div", class_="bbCodeBlock-expandContent ")
                for school_message in school_messages:
                    for _key in self.keyword():
                        if _key not in school_message.text:
                            continue
                        # Get the text of the messages.
                        if _key.lower() in school_message.text.lower():
                            ret_page = page_num
                            message_content = school_message.text
                            found[message_content] = page_num
                            break
                
                # Check if done searching for school
                if ret_page != -1 and self.recency != 'all':
                    break
            content.append(found)

        return content            


    @staticmethod
    def guess_school(search: list, query: list) -> list:
        if query is None:
            return search
        lst = []
        bad_query = []
        for _q in query:
            found = None
            REMOVE = ['School of Medicine', '-', '@', 'Medical College', '.']
            for regex in REMOVE:
                _q = _q.replace(regex, '')
            # Remove keywords from the query that will complicate things.
            for val in search:
                # Save a copy of the original school name before modification.
                school_name = '%s' % val
                for regex in REMOVE:
                    val = val.replace(regex, '')
                # First, let's check if the name already directly matches.
                if _q.lower() in val.lower() or val.lower() in _q.lower():
                    # Edge case: 'Charles R Drew @ UCLA' contains UCLA but
                    # that's not what people mean when they query UCLA.
                    if _q.lower() == 'ucla' and 'drew' in val.lower():
                        pass
                    else:
                        found = school_name
                        break
                # Next, let's check if the abbreviation matches.
                # This works for schools like UCLA, UCSF, etc.
                regex = re.compile('[^a-zA-Z]')
                abbrev = ''
                for c in regex.sub('', val):
                    abbrev += c if c.isupper() else ''
                abbrev = abbrev.lower()
                if _q.lower() in abbrev or abbrev in _q.lower():
                    found = school_name
                    break
                # Next, let's handle schools that start with "University of"
                # where people often abbreviate as UWisconsin, UChicago, UPenn,
                # etc.
                if 'University of'.lower() in val.lower():
                    # Remove 'University of' from the string.
                    abbrev = 'U' + val[len('University of'):]
                    abbrev = abbrev.lower()
                    if _q.lower() in abbrev or abbrev in _q.lower():
                        found = school_name
                        break
                # Finally, if none of the above methods work, we'll split
                # the query by spaces and test each word individually.
                for s_query in _q.split(' '):
                    # Ignore small general words like 'of.' 
                    if (s_query.lower() in val.lower() or
                            val.lower() in _q.lower()) and len(s_query) > 2:
                        found = school_name
                        break
            if found is not None:
                lst.append(found)
            else:
                bad_query.append(_q)
        return lst, bad_query



#     print(school_names[i])
 #    print("    " + school_url)
  #   if (first_page == -1):
   #     print("    Keyword not found for this school.")
   # else:
   #     print("    First Page Instance: " + str(first_page))
   #     newline_char_pos = message_content[1:].find('\n')
   #     if (newline_char_pos == -1):
   #         print("    Initial Message Content: " + message_content[1:])
   #     else:
   #         print("    Initial Message Content: " + message_content[1:newline_char_pos])
   # print()
