"""Copyright Michael Yao 2022.

Web scraper to read data from Student Doctor Network.
"""
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

class SDNScraper:
    # If the only punctuation there is is a question mark, then no helpful
    # information was provided.
    EXCLUDE = ['?']
    PUNCTUATION = ['.', '!']

    # Keywords for common queries.
    KEYWORDS_SECONDARY = ['secondary received', 'secondary']
    KEYWORDS_INVITE = ['ii ', 'ii!', 'interview invite']
    KEYWORDS_DECISION = ['a.', 'a!', 'w.', 'w!', 'r.', 'accepted!', 'waitlisted', 'rejected']
    KEYWORDS_FIN_AID = ['aid', 'finaid', 'fin aid', 'financial aid']

    # URLs for School Lists
    SDN_URL = 'https://forums.studentdoctor.net'
    URLS = { '2021-2022': 'https://forums.studentdoctor.net/threads/2021-2022-alphabetical-listing-of-schools.1440875/',
             '2020-2021': 'https://forums.studentdoctor.net/threads/2020-2021-alphabetical-listing-of-schools.1406109/',
             '2019-2020': 'https://forums.studentdoctor.net/threads/2019-2020-alphabetical-listing-of-schools.1374208/',
             '2018-2019': 'https://forums.studentdoctor.net/threads/2018-2019-all-school-discussions-alphabetical-list.1350681/' }

    def __init__(self, data):
        """Initialize web scraper class."""
        # Get the desired page.
        self.year = data['year'].replace('-', '')
        self.page = requests.get(SDNScraper.URLS[data['year']])

        # Generate list of schools.
        soup = BeautifulSoup(self.page.content, 'html.parser')
        results = soup.find("div", class_="bbWrapper")
        school_sites = results.find_all("a", class_="link link--internal")
        school_names_urls = {}
        for site in school_sites:
            school_names_urls[site.text[10:]] = site['href']

        # Get requested school query.
        schools_req = []
        MAX_SCHOOL_COUNT = 10
        for i in range(MAX_SCHOOL_COUNT):
            inpt = data.get("school-" + str(i + 1), "")
            if inpt is None or not isinstance(inpt, str) or len(inpt) == 0:
                continue
            schools_req.append(inpt.lower())
        self.schools_req_list = schools_req
        self.school_inputs = "-".join(schools_req)
        self.school_inputs = self.school_inputs.replace(" ", "_")

        self.school_query = SDNScraper.guess_school(school_names_urls.keys(),
                                                    query=schools_req)
        if self.school_query is not None:
            self.school_query = self.school_query[0]
        else:
            self.urls = None
            return
        urls = []
        for site in school_names_urls.keys():
            if site in self.school_query:
                urls.append(school_names_urls[site])
        self.urls = urls

        # Get the type of data to return.
        self.recency = data.get("recency", "").lower()
        self.recency_input = data.get("recency", "").replace(" ", "_")

        # Get the keyword to search for.
        self.keyword = data.get("keyword", "").lower()
        self.keyword_input = data['keyword'].lower().replace(" ", "_")
        if self.keyword == 'something else':
            # TODO
            self.keyword = data['opt-keyword'].lower()
            assert self.keyword is not None
            assert len(self.keyword) > 0
            self.keyword = [self.keyword]
        elif self.keyword == 'secondaries':
            self.keyword = SDNScraper.KEYWORDS_SECONDARY
        elif self.keyword == 'interview invites':
            self.keyword = SDNScraper.KEYWORDS_INVITE
        elif self.keyword == 'decisions':
            self.keyword = SDNScraper.KEYWORDS_DECISION
        elif self.keyword == 'financial aid':
            self.keyword = SDNScraper.KEYWORDS_FIN_AID
        else:
            raise ValueError('Unrecognized Keyword!')


    def scrape(self, export: bool = False) -> str:
        """Scrape SDN for relevant content."""
        content = []
        if self.urls is None:
            return content
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
            # Try to retrieve max page number:
            for entry in nav_sites:
                input = entry.find('input')
                if isinstance(input, int) and input == -1:
                    continue
                elif input is not None:
                    max_page = input.get('max')
                    break
            nav_sites = [_site.find('a').get('href') for _site in nav_sites if
                         not ((isinstance(_site.find('a'), int) and
                         _site.find('a') == -1) or _site.find('a') is None)]
            nav_sites = [SDNScraper.SDN_URL + _site for _site in nav_sites
                         if _site is not None]
            # Fill in the gaps of the pages with no URLS.
            if len(nav_sites) > 3:
                first_site = nav_sites[-2].split('-')
                first_site = first_site[-1]
                last_site = nav_sites[-1].split('-')[-1]
                first_site = int(first_site) if first_site.isnumeric() else 3
                last_site = int(last_site) if last_site.isnumeric() else max_page
                for i in range(first_site + 1, last_site):
                    nav_sites.append(nav_sites[0].split('page')[0] + 'page-' +
                                     str(i))
            elif len(nav_sites) == 0:
                nav_sites = [school_url]
            base_url = nav_sites[0]
            nav_sites = sorted(nav_sites[1:], key=lambda x: int(x.split('-')[-1]))
            nav_sites.insert(0, base_url)

            ret_page = -1
            message_content = ""
            found = {}

            page_nums = range(0, len(nav_sites))
            if self.recency == 'most recent':
                page_nums = reversed(page_nums)
            for page_num in page_nums:
                # Send page request
                page_url = nav_sites[page_num]
                school_page = requests.get(page_url)
                school_soup = BeautifulSoup(school_page.content, 'html.parser')
                # Retrieve the messages on the page
                school_messages = school_soup.find_all("div", class_="message-content")
                for body in school_messages:
                    school_message = body.find_all("div", class_="bbWrapper")
                    if school_message is None:
                        continue
                    user_content = body.find_all("div", class_="message-userContent")
                    user = 'Unknown'
                    date = 'Unknown'
                    if user_content is not None:
                        user = user_content[0].get('data-lb-caption-desc').split()
                        date = ' '.join(user[-6:-3])
                        user = user[0]

                    school_message = school_message[0]
                    for _key in self.keyword:
                        if _key not in school_message.text:
                            continue
                        if len(school_message.text) > 50:
                            continue
                        if "?" in school_message.text:
                            continue
                        if (_key == "a." or _key == "a!") and len(school_message.text) > 5:
                            continue
                        if (_key == "w." or _key == "w!") and len(school_message.text) > 5:
                            continue
                        if _key == "r." and len(school_message.text) > 5:
                            continue
                        # Get the text of the messages.
                        if _key.lower() in school_message.text.lower():
                            # Get the page number that we're on.
                            ret_page = page_num
                            # Get the text of the message
                            message_content = school_message.text
                            # Remove any inner messages.
                            message_content = message_content.split('Click to expand...')[-1]
                            found[message_content] = [page_num + 1, user, date]
                            break

                # Check if done searching for school
                if ret_page != -1 and self.recency != 'all':
                    break
            if len(found) == 0:
                content.append(None)
            else:
                content.append(found)

        if not export:
            return json.dumps(content)
        FINAL = ""
        HEADERS = ["Message", "SDN Page Number", "Author Username", "Date Posted"]
        for i in range(len(content)):
            p = []
            # Final output string.
            try:
                f = '"' + self.schools_req_list[i].replace('"', '""').upper() + '"' + '\n'
            except IndexError:
                f = "\n"
            # Format HEADERS to CSV string.
            for h in HEADERS:
                f += '"' + h.replace('"', '""') + '"' + ','
            f = f[:-1] + '\n' if len(f) > 0 else f
            # Format message entries to CSV string.
            for key in content[i]:
                d = datetime.strptime(content[i][key][2], '%b %d, %Y')
                s = '"' + key.replace('"', '""') + '"' + ','
                s += '"' + str(content[i][key][2]).replace('"', '""') + '"' + ','
                s += '"' + str(content[i][key][0]).replace('"', '""') + '"' + ','
                s += '"' + str(content[i][key][1]).replace('"', '""') + '"' + '\n'
                p.append([d, s])
            # Sort message strings by date.
            p = sorted(p, key=lambda x: x[0],
                       reverse=(self.recency == 'most recent'))
            for i in range(len(p)):
                f += p[i][1]
            f += "\n"
            FINAL += f

        return FINAL


    @staticmethod
    def guess_school(search: list, query: list) -> list:
        """Guess formatted school name in search from query."""
        if query is None:
            return None
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
                # Before anything, check edge case: 'Charles R Drew @ UCLA'
                # contains UCLA but that's not what people mean when they query
                # UCLA.
                if _q.lower() == 'ucla' and 'drew' not in val.lower():
                    found = 'University of California - Los Angeles (Geffen)'
                    break
                # First, let's check if the name already directly matches.
                if _q.lower() in val.lower() or val.lower() in _q.lower():
                    found = school_name
                    break
                # Next, let's check if the abbreviation matches.
                # This works for schools like UCLA, UCSF, etc.
                regex = re.compile('[\W_0-9]+')
                regex = regex.sub('', val)
                abbrev = ''
                for i in range(len(regex)):
                    abbrev += regex[i] if regex[i].isupper() else ''
                abbrev = abbrev.lower()
                if _q.lower() in abbrev:
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
