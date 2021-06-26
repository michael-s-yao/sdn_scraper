import requests
from bs4 import BeautifulSoup

# DEFAULT PARAMETERS
keyword_interview_invite = "Ii"
keyword_secondary = "Secondary"

# MODIFY KEYWORD HERE
keyword = keyword_interview_invite

URL = "https://forums.studentdoctor.net/threads/2020-2021-alphabetical-listing-of-schools.1406109/"
page = requests.get(URL)

soup = BeautifulSoup(page.content, 'html.parser')

results = soup.find("div", class_="bbWrapper")

school_sites = results.find_all("a", class_="link link--internal")

school_names = []
school_urls = []

for site in school_sites:
    school_names.append(site.text[10:])
    school_urls.append(site['href'])

# Default value is 10. Change if additional pages for a particular school
max_page_search = 10

print("Keyword: " + keyword + "\n")

# Parse through every school in the list
for i in range(len(school_urls)):
    # Parse through every page on the school-specific page
    school_url = school_urls[i]
    # Send preliminary page request to determine number of pages
    init_school_page = requests.get(school_url)
    init_school_soup = BeautifulSoup(init_school_page.content, 'html.parser')
    school_navigation = init_school_soup.find("ul", class_="pageNav-main")
    # Handle the case where only one page for the school
    if school_navigation is None: nav_sites=["-1"]
    # Handle the general case of multiple pages for the school
    else: nav_sites = school_navigation.find_all("li")

    first_page = -1
    message_content = ""

    for page_num in reversed(range(1, len(nav_sites) + 1)):
        # Send page request
        school_page = requests.get(school_url + "page-" + str(page_num))
        school_soup = BeautifulSoup(school_page.content, 'html.parser')
        # Retrieve the messages on the page
        school_messages = school_soup.find_all("div", class_="bbCodeBlock-expandContent ")
        for school_message in school_messages:
            if (keyword == keyword_secondary) or (keyword == keyword_interview_invite):
                relevant = ("Receive" in school_message.text) or ("receive" in school_message.text)
            else: relevant = True
            # Get the text of the messages
            if (keyword.upper() in school_message.text) and relevant:
                first_page = page_num
                message_content = school_message.text
                break
            elif (keyword.lower() in school_message.text) and relevant:
                first_page = page_num
                message_content = school_message.text
                break
            elif (keyword in school_message.text) and relevant:
                first_page = page_num
                message_content = school_message.text
                break
        
        # Check if done searching for school
        if (first_page != -1):
            break

    print(school_names[i])
    print("    " + school_url)
    if (first_page == -1):
        print("    Keyword not found for this school.")
    else:
        print("    First Page Instance: " + str(first_page))
        newline_char_pos = message_content[1:].find('\n')
        if (newline_char_pos == -1):
            print("    Initial Message Content: " + message_content[1:])
        else:
            print("    Initial Message Content: " + message_content[1:newline_char_pos])
    print()
