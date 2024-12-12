import mailbox
import json
from datetime import datetime
import re
import quopri
import os.path


class EmailClass:
    def __init__(self, date, body, to_student, sentDatePattern, normalPattern):
        self.date = date
        self.body = body
        self.to_student = to_student
        self.sentDatePattern = sentDatePattern
        self.normalPattern = normalPattern

    def encode_decode_txt(self):
        try:
            quopri.decodestring(self.body)
        except Exception:
            pass
        try:
            self.body.encode('ascii', 'ignore').decode('utf-8')
        except Exception:
            pass

    def look_for_date_in_msg(self, prev_date_pattern):
        # prev_date_pattern is the EXACT match of the reply date text in the email. ie, "On x x day, x .com wrote:"
        # also is From: to Subject line end.
        match_all = re.search(r"(?:Sent|Date).*", prev_date_pattern) # if u do dotall itll match w everything after Sent|Date
        reply_date_format = ""
        remove_char_prev_date = ""

        if match_all:
            match_once = match_all.group()
            print(match_once)
            findFormat = re.search("Sent:", match_once, re.DOTALL)
            if findFormat:
                find_seconds = re.search(r"\d{1,2}:\d{1,2}:\d{1,2} (?:AM|PM)", match_once)
                if find_seconds:
                    reply_date_format = 'Sent: %A, %B %d, %Y %I:%M:%S %p'
                else:
                    reply_date_format = 'Sent: %A, %B %d, %Y %I:%M %p'
                remove_char_prev_date = match_once
            elif any(item in match_once for item in 'Date:'):
                find_if_slash = re.search(r"\d{1,2|/\d{1,2}/\d{1,2}", match_once)
                if find_if_slash:
                    find_AMPM = re.search(r"AM|PM", match_once).end()
                    match_once = match_once[:find_AMPM]

                    reply_date_format = 'Date: %m/%d/%y %I:%M %p'
                else:
                    reply_date_format = 'Date: %A, %b %d, %Y, %I:%M %p'
                remove_char_prev_date = match_once
            remove_char_prev_date = re.sub(r"\s+", " ", remove_char_prev_date, re.DOTALL)
            remove_char_prev_date = re.sub(r"\n", "", remove_char_prev_date, re.DOTALL)
            remove_char_prev_date = remove_char_prev_date.strip()

        elif "wrote:" in prev_date_pattern:
            # only the pattern that goes ", at " has this specific pattern that does not require a "%a.
            # excluding Sent or Date formatting style.
            # the rest is like '%a %b %d %Y %I:%M %p' once commas and other words are stripped, but we are also removing
            # %a part as well at the end when matching only starting at %b using regex
            # make everything same as this.

            # "On Fri, Sep 13, 2019, 08:16 Abraham Kang <notifications@instructure.com>"
            prev_date_pattern = prev_date_pattern.replace("at", "")
            prev_date_pattern = re.sub(r"\s+", " ", prev_date_pattern, re.DOTALL)
            prev_date_pattern = re.sub(r"\n", "", prev_date_pattern, re.DOTALL)

            match1 = re.search(r"\b[A-Za-z]{3} \d{1,2}, \d{4},* \d{1,2}:\d{1,2}", prev_date_pattern, re.DOTALL)
            if match1:
                remove_char_prev_date = match1.group(0).replace(",", "")
                reply_date_format = '%b %d %Y %H:%M'
                print("MATHC!1")
            else:
                stripping_pattern = prev_date_pattern.replace(",", "").replace("at", "").replace("On", "").replace("wrote:", "")
                match = re.search(r"\b[A-Za-z]{3} \d{1,2} \d{4} \d{1,2}:\d{2} (?:AM|PM)", stripping_pattern)
                match2 = re.search(r"\d{1,2} [A-Za-z]{3} \d{4} \d{1,2}:\d{1,2}", stripping_pattern, re.DOTALL)
                #  On Friday, July 21, 2023 at 02:13:14 PM EDT, Abraham Kang <notifications@instructure.com> wrote:
                match3 = re.search(r"\b\w+\b \d{1,2} \d{4} \d{1,2}:\d{2}:\d{2} (?:AM|PM)", stripping_pattern)
                # On Fri, Sep 13, 2024 at 9:49AM Paul Donner  <notifications@instructure.com>
                match4 = re.search(r"\b[A-Za-z]{3} \d{1,2} \d{4} \d{1,2}:\d{2}(?:AM|PM)", stripping_pattern)

                if match:
                    print("MATCH")
                    remove_char_prev_date = match.group()
                    reply_date_format = '%b %d %Y %I:%M %p'
                elif match2 and not match:
                    print("MATCH2")
                    remove_char_prev_date = match2.group()
                    reply_date_format = '%d %b %Y %H:%M'
                elif match3:
                    print("MATCH3")
                    remove_char_prev_date = match3.group()
                    reply_date_format = '%B %d %Y %I:%M:%S %p'
                elif match4:
                    print("MATCH4")
                    remove_char_prev_date = match4.group()
                    reply_date_format = '%B %d %Y %I:%M:%S%p'


        else:
            print("something went wrong, fix it")
            exit()

        reply_obj = datetime.strptime(remove_char_prev_date, reply_date_format)
        # so that while iterating through the for loop, if i come across emails that have these
        # exact dates, i don't process them again. and since i already sorted the list of emails
        # based on the most recent dates, i'll be processing the ones that are the most recent
        # first.
        return reply_obj


    """def find_dates_of_replies(self):
        reply_matches = re.finditer(self.reply_date_pattern, body, re.DOTALL)
        match_group = [match.group().encode('ascii', 'ignore').decode('utf-8') for match in reply_matches]
        return match_group
    """
    def find_who_from(self, prev_match, prof_name_and_email_list):
        who_from = ""
        # prev_match is the previous reply format EXACTLY. ie. "On x x day from x@gmail.com wrote:" or the other version.
        if prev_match:
            sentDateCheck = re.search(r"From:.*?(?:Date:|Sent:)", prev_match, re.DOTALL)
            if sentDateCheck:
                print("HErE")
                print(prev_match)
                # check who sent the email, so that i can use it to create the header of "Student" or "Professor",
                who_from = sentDateCheck.group()
                who_from = who_from.replace("From:", "").replace("\nDate:", "").replace("\nSent:", "").replace("*", "")
            elif any(item in prev_match for item in ["wrote:"]):
                print("OT HERE")

                # On 9 Aug 2020 18:38, Abraham Kang <notifications@instructure.com> wrote:"
                match = re.search(r"On \d{1,2} [A-Za-z]{3} \d{4} \d{1,2}:\d{1,2}\s*(.+?)\n*wrote:", prev_match, re.DOTALL)
                #"On Mar 11, 2020, (or no comma) at 11:44, Abraham Kang <notifications@instructure.com> wrote:"
                match1 = re.search(r"\b[A-Za-z]{3} \d{1,2}, \d{4},* at \d{1,2}:\d{1,2},\s*(.+?)\n*wrote:", prev_match, re.DOTALL)
                #"On Fri, Sep 13, 2019, 08:16 Abraham Kang <notifications@instructure.com>"
                match2 = re.search(r"\b[A-Za-z]{3} \d{1,2}, \d{4}, \d{1,2}:\d{1,2}\s*(.+?)\n*wrote:", prev_match, re.DOTALL)
                #"On Fri, 6 Sep 2019 at 00:17, T.I. Scott <thomas.ian.scott@gmail.com> wrote:")
                match3 = re.search(r"\d{1,2} [A-Za-z]{3} \d{4} at \d{1,2}:\d{1,2},\s*(.+?)\n*wrote:", prev_match, re.DOTALL)
                # On Sep 12, 2024 at 7:31 PM,  <Paul Donner Public (mailto:pdonner@truenollc.net)>  wrote:
                # On Fri, Sep 13, 2024 at 9:49AM Paul Donner  <notifications@instructure.com>
                match4 = re.search(r"(?:AM|PM),*\s*(.+?)wrote:", prev_match, re.DOTALL)
                # On Friday, July 21, 2023 at 02:13:14 PM EDT, Abraham Kang <notifications@instructure.com> wrote:
                match5 = re.search(r"(?:AM|PM) [A-Za-z]{3},\s*(.+?)wrote:", prev_match, re.DOTALL)

                if match:
                    who_from = match.group(1)
                elif match1:
                    who_from = match1.group(1)
                elif match2:
                    who_from = match2.group(1)
                elif match3:
                    who_from = match3.group(1)
                elif match4:
                    who_from = match4.group(1)
                elif match5:
                    who_from = match5.group(1)
                else:
                    print("who form is not found. fix it")
                    exit()
                print(f"who from is {who_from}")
                print(f"prev match HErE IS NOW {prev_match}")
                #
                # who_from = who_from_all[0]

                who_from = re.sub("<|>", "", who_from)
                print(who_from)
            else:
                print("i really screwed up somewhere")
                exit(5)
        else:
            print("HOW ThE FU")
            exit(10)
        print(who_from)
        name_sign_offs = who_from.split()

        print(name_sign_offs)
        if any(item in who_from for item in prof_name_and_email_list):
            email_header = 'Professor'
            print("heade ri sprof")
        else:
            email_header = 'Student'
            print("student student sutdent")
            # only save up to second last element. last element = email.
            # pretend there are no suffixes. but there are suffixes. so..yeah.

        return name_sign_offs, email_header

    def remove_sign_offs(self, part_of_reply, name_sign_offs, email_header, email_address):
        suffix_list = ["I", "II", "III", "IV", "Jr.", "Sr."]
        while len(name_sign_offs) > 0:
            if any(item in name_sign_offs for item in suffix_list):
                # concatenate second to last element + suffix
                # so when removing the suffix it won't remove things like
                # "Part III" to "Part " in the email
                suffix = name_sign_offs.pop(-1)

                concat_suffix_to_last = name_sign_offs[-1] + f" {suffix}"
                name_sign_offs[-1] = concat_suffix_to_last

            name_to_remove = ' '.join(name_sign_offs)
            print(name_to_remove)

            potential_sign_off_str = f"\n{name_to_remove}"
            match = re.search(potential_sign_off_str, part_of_reply, re.IGNORECASE)
            if match:
                # if sender repeats their own name after a newline, delete it. most likely signature.
                # having this is nice because sometimes someone's sign off looks like this:
                # Brian Johnson
                # PhD at Stanford University
                # by specifically looking for the name during sign off i can remove everything that comes after
                part_of_reply = part_of_reply[:match.start() - 1]

            # now remove all the names present in the email.
            part_of_reply = re.sub(name_to_remove, "", part_of_reply)
            name_sign_offs.pop(-1)

        if email_address:
            if type(email_address) == str:
                email_address = [email_address]

            for element in email_address:
                part_of_reply = re.sub(element, "", part_of_reply)
                element = re.sub(r">|<", "", element)
                part_of_reply = re.sub(element, "", part_of_reply)

        hibye_list = [r"\bHi\b", r"\bHello\b", r"\bAbe\b", r"\bKang\b", r"\bAbraham\b", r"\bGood morning\b"
                      "thanks", "regards", r"\bmy best", "[**EXTERNAL EMAIL**]"
                      r"\bbest", r"\bdear", "sincerely", "Thanks"
                      r"\bmr.", r"\bmr\b", r"\bprof\b", "professor", r"\bsir\b",
                      r"--\b", r"\s\.\s", r"\s,\s", r"\bHi[,-]\b", r"\bAdios\b"]

        for _ in hibye_list:
            # find and remove the greeting or sign off
            part_of_reply = re.sub(_, '', part_of_reply, flags=re.IGNORECASE)

        trailing_deletions = ["Sent from my", r"\[image: ", r"[cid:", "You can reply to this message", "(Facillitator)"
                              "You can reply to ts message", "The contents of this email are", "<x-msg"]

        # just to make sure all the trailing things have been deleted, if there was no name sign off.
        for one_trailing in trailing_deletions:
            match = re.search(one_trailing, part_of_reply, re.IGNORECASE)
            if match:
                # ("found trailing messages/links from Canvas to delete. Deleting...")
                part_of_reply = part_of_reply[:match.start() - 1]

        part_of_reply = re.sub(r"\n(?:> )+", '\n', part_of_reply)
        part_of_reply = re.sub(r">>", '', part_of_reply)
        part_of_reply = re.sub(r" >\B", '', part_of_reply)
        part_of_reply = re.sub(r"\B>\B", '', part_of_reply)
        part_of_reply = re.sub(r"show quoted text <(?s:).*?_>", '', part_of_reply)
        part_of_reply = re.sub(r"show quoted text", '', part_of_reply)
        part_of_reply = re.sub(r"\[\*\*EXTERNAL EMAIL\*\*]:", '', part_of_reply)
        part_of_reply = f"{email_header}: {part_of_reply}"
        print("\n\n\n\nTHIS")

        print(part_of_reply)
        print("THIS\n\n\n\n\n")
        return part_of_reply

    def filter_for_reply_dates(self, email_info_dict, recipient, prof_email):
        prev_match = ""
        email_address = ""
        email_chain = []
        counter = 0
        lastEmail = False
        from_index = ""
        prof_name_and_email_list = ["Abe", "Abraham", "Kang", "akang@ecornell.com", "ak16@cornell.edu"]

        reply_date_pattern = rf"({self.sentDatePattern})|({self.normalPattern})"
        match_test = re.search((self.normalPattern), self.body, re.DOTALL)
        match_test2 = re.search((self.sentDatePattern), self.body, re.DOTALL)

        if match_test:
            print(match_test.group())
            print("match test goes through")
        elif match_test2:
            print(match_test2.group())
            print("match test goes through")

        while not lastEmail:
            print("NOT LAST EMAIL. going thru the loop")
            match_all = re.findall(reply_date_pattern, self.body, re.DOTALL)
            # first find all the reply date patterns in the body.
            if match_all:
                print("match all is correct")
                match_once = match_all[0]
                for half_match in match_once:
                    if re.search("Sent|Date", half_match, re.DOTALL):
                        from_index = self.body.find('From:')
                        print(f"FROM INDEXX IS {from_index}")
                        subject_index = self.body.find('message in Canvas.')
                        print(f"SUBJECT INDEX IS {subject_index}")
                        len_sub_index = len('message in Canvas.')
                        subject_index_end = subject_index + len_sub_index
                        print(f"END OF SUB INDEX IS {subject_index_end}")
                        next_date_format = self.body[from_index:subject_index_end]
                        print(f"NEXT DATE FORMAT IS {next_date_format}")

                    elif re.search("wrote:", half_match, re.DOTALL):
                        complete_pattern = re.search(self.normalPattern, self.body, re.DOTALL)
                        if complete_pattern:
                            from_index = complete_pattern.start()
                            subject_index_end = complete_pattern.end()
                        next_date_format = self.body[from_index:subject_index_end]
                        print(f"NEXT DATE FORMAT IS {next_date_format}")

                    # if found, then find the first reply date pattern and the index for it.
                    # find the index starting from "On" to "wrote:" Or "From:" to the end of the subject line.

                # one email is up to right before the reply date format that is the header for the next quoted email.
                one_email = self.body[:from_index - 1]
                # ("one email is the email BEFORE the matched reply format")
                self.body = self.body[subject_index_end:]

                # counter == 0 it is still at the most top/recent email, before the quote history.
                # for the most recent email, find who wrote it based on who sent it using to_student.
                if counter == 0:
                    # if to_student is True, it means email was sent from professor to student.
                    if email_info_dict['to_student']:
                        email_header = 'Professor'
                        name_sign_offs = ['Abe', 'Abraham', 'Kang']
                        email_address = prof_email
                    else:
                        email_header = 'Student'
                        name_sign_offs = recipient.split()

                        email_address = name_sign_offs.pop(-1)

                        # in real parser, make sure to check for suffixes.
                else:
                    name_sign_offs, email_header,  = self.find_who_from(prev_match, prof_name_and_email_list)
                    email_address = name_sign_offs.pop(-1)



                print(f"name sign offs is {name_sign_offs}")
                one_email = self.remove_sign_offs(one_email, name_sign_offs, email_header, email_address)
                counter += 1

                email_chain.append(one_email)
                prev_match = next_date_format
                print(f"{prev_match} prev match")

            elif not re.search(reply_date_pattern, self.body, re.DOTALL):
                if counter == 0:
                    print(" single email with no response. skip")
                else:
                    name_sign_offs, email_header = self.find_who_from(prev_match, prof_name_and_email_list)
                    lastEmail = self.remove_sign_offs(self.body, name_sign_offs, email_header, email_address)

                    email_chain.append(lastEmail)
                lastEmail = True

        return email_chain, prev_match


def getcharsets(msg):
    charsets = set({})
    for c in msg.get_charsets():
        if c is not None:
            charsets.update([c])
    return charsets


def get_message_body(msg):
    msg_body = "null"
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                for subpart in part.walk():
                    if subpart.get_content_type() == 'text/plain':
                        # get subpart payload
                        msg_body = subpart.get_payload(decode=True)
                    elif subpart.get_content_type() == 'html':
                        body_html = subpart.get_payload(decode=True)

    elif msg.get_content_type() == 'text/plain':
        msg_body = msg.get_payload(decode=True)

    if msg_body != "null":
        for charset in getcharsets(msg):
            try:
                msg_body = msg_body.decode(charset)
            except UnicodeDecodeError:
                pass
                # handleerror("UnicodeDecodeError: encountered.", msg, charset)
            except AttributeError:
                pass
                # handleerror("AttributeError: encountered", msg, charset)

        try:
            quopri.decodestring(msg_body)
        except Exception:
            pass

        try:
            msg_body.encode('ascii', 'ignore').decode('utf-8')
        except Exception:
            pass
    return msg_body


def parse_box(mbox_file, prof_email):
    mbox = mailbox.mbox(mbox_file)
    emails = {}
    # key = subject, value = list of dicts containing emails that has that subject line
    for message in mbox:
        if any(item in message['From'] for item in prof_email):
            recipient = 'To'
            to_student = True
        else:
            recipient = 'From'
            to_student = False

        email_dict = {'to_student': to_student}
        recipient = message.get_all(recipient, [])

        if to_student:
            recipient = recipient.extend(message.get_all('CC', []))

        # if recipient is None, skip.
        if recipient is None:
            print("no recipient found. Skipping...")
            continue
        elif type(recipient) is list:
            if len(recipient) > 1:
                print("group email. skipping")
                continue
            elif len(recipient) == 1:
                recipient = recipient[0]

        print("recipient found.")
        # if the person Abraham is talking to is colleagues or helpdesk or multiple people, disregard email
        DISREGARD_ADDR = ["@ecornell.com", "@cornell.edu", "groups.cornell.edu", "undisclosed-recipient:;"]
        if any(item in recipient for item in DISREGARD_ADDR):
            print("recipient is colleague or helpdesk. looping the next element of the for loop.")
            continue

        recipient_trailing = [" via ", " ("]
        for trailing in recipient_trailing:
            if trailing in recipient:
                recipient = recipient.split(trailing)[0]

        print("recipient processed.")
        print(recipient)
        email_dict.update({"recipient": recipient})
        print("\n")

        # message['Date'] = Thu, 11 Sep 2024 17:27:30 +0000
        # [5:-9] changes it to 11 Sep 2024 17:27

        # assumes subject line is empty until proven otherwise in the below if-else loop
        setEmpty = True
        new_subject = message['Subject']
        print(f'subject line: {new_subject}')

        # need this if statement, if subject is nonetype then it will get error with lower()
        if message['Subject'] is None:
            print("subject is none. Escaping the if else loop.")
            pass
        # if subject line starts with "Re: " then remove it
        elif message['Subject'].lower().startswith(
                're:'):  # or message['Subject'].startswith('RE:') or message['Subject'].startswith('re:'):
            new_subject = re.sub("Re:", "", message['Subject'], flags=re.IGNORECASE)
            # remove leading and trailing whitespaces. (Some subject lines are just "re:" with no space. so removing
            # leading/trailing spaces needs to be a separate event.
            new_subject = new_subject.strip()
            print("subject line starts with Re:. removing...")

            # check if subject is empty or only has whitespace. because there's
            # some subject lines that are literally just "Re: ".
            if new_subject:
                print("since subject line is not empty, setEmpty is set as False.")
                setEmpty = False
        elif message['Subject'].lower().startswith('re: external: re: '):
            # or message['Subject'].startswith('RE:') or message['Subject'].startswith('re:'):
            new_subject = re.sub("Re:", "", message['Subject'], flags=re.IGNORECASE)
            # remove leading and trailing whitespaces. (Some subject lines are just "re:" with no space. so removing
            # leading/trailing spaces needs to be a separate event.
            new_subject = new_subject.strip()
            print("subject line starts with Re: External: Re: . remomving...")

            # check if subject is empty or only has whitespace. because there's
            # some subject lines that are literally just "Re: ".
            if new_subject:
                print("since subject line is not empty, setEmpty is set as False.")
                setEmpty = False

        # if subject line is a string, aka not empty/false:
        elif message['Subject']:
            print("since subject line is not empty, setEmpty is set as False.")
            setEmpty = False

        # subject is blank, has white spaces, or is just called 'Re:'
        if setEmpty:
            new_subject = recipient + " with No Subject"
        elif not setEmpty:
            new_subject = new_subject.replace("\n", "")
            if " just sent you a message" in new_subject:
                new_subject = new_subject.split(" just sent you a message")[0]
        print(f'new subject line is: ' + new_subject)

        email_dict.update({'Date': message['Date']})

        # find all the emails' subject lines and dates. we want to order all emails with the same subject by date.
        # find if subject already exists, and if so, add to existing list
        body = get_message_body(message)
        if body != "null":
            if any(item in body for item in ["---------- Forwarded message ---------", "--------------- Original Message -------------"]):
                print("email is a forwarded message. skipping...")
                continue
            elif any(item in body for item in DISREGARD_ADDR):
                print("email indicates some messages are from or directed to a colleague/helpdesk. Skipping...")
                continue

            email_dict.update({'Body': body})
            if new_subject not in emails:
                emails[new_subject] = [email_dict]
            elif new_subject in emails:
                # find duplicates
                if not any(d['Body'] == body for d in emails[new_subject]):
                    # this is a list of dictionaries
                    new_list = emails[new_subject]
                    new_list.append(email_dict)
                    emails[new_subject] = new_list
                elif any(d['Body'] == body for d in emails[new_subject]):
                    pass

        elif body == "null":
            continue

    print("Passed parsing body")
    for email_subject_key in emails:
        # retrieve the value of the key 'subject' from each dictionary
        # group_email_list is a list of dictionaries containing date, to, from, body information of emails
        group_email_list = emails[email_subject_key]
        # remove all the emails where it got an error decoding the body of the email and returned null
        # group_email_list = list(filter(lambda item: item.get('body') == 'null', group_email_list))

        # commented out the code here because i removed dupes above
        # remove dupes
        # unique_group_email_list = []
        # for d in group_email_list:
        #    if d not in unique_group_email_list:
        #        unique_group_email_list.append(d)

        # first sort emails by most recent
        # unique_group_email_list = unique_group_email_list.sorted(key=lambda x: x['date'])

        group_email_list = sorted(group_email_list, key=lambda x: x['Date'])
        print("sorting email list based on date")

        # now remove seconds and timezone, because quoted replies in email don't have that data.
        # timezone/seconds was only to make sure to sort the emails in order.
        # ** allows arbitrary number of d dicts, then it iterates over all those and replaces the current date values
        # group_email_list = [{**d, 'date': d['Date'].replace(tzinfo=None).strftime("%Y-%m-%d %H:%M")} for d in group_email_list]

        for email_info_dict in group_email_list:
            email_info_dict['Date'] = str(email_info_dict['Date'])

    scriptpath = os.path.dirname(__file__)
    filename = os.path.join(scriptpath, 'group_of_email.json')

    with open(filename, "a") as outfile:
        json.dump(emails, outfile, indent=4)


def create_filtered_email_dialogue(prof_email):
    dialogue_style_email_list = []
    reply_dates_list = []
    with open("group_of_email.json", "r") as outfile:
        emails = json.load(outfile)
        # emails = dictionary containing lists of dictionaries
        for subject_key, group_email_list in emails.items():
            # group_email_list = lists of dictionaries
            for email_info_dict in group_email_list:
                for key, values in email_info_dict.items():
                    if key == "Date":
                        match_date_str = re.search(r'\d{1,2}\s[A-Za-z]{3}\s\d{4}\s\d{2}:\d{2}:\d{2}\s[+-]\d{4}', email_info_dict['Date'])
                        date_format = '%d %b %Y %H:%M:%S %z'
                        date_obj = datetime.strptime(match_date_str.group(), date_format)
                if date_obj not in reply_dates_list:
                    print("this email has not yet been processed/is a new email thread, as there it shares no same date "
                          "as another email. Processing:")
                    print("\n")
                    # we need to remove all the names from the emails.
                    # first two elements are name of sender

                    # retrieve body
                    print("not stuck")
                    body = email_info_dict['Body']
                    to_student = email_info_dict['to_student']
                    recipient = email_info_dict['recipient']

                    example_object = EmailClass(date_obj, body, to_student, sentDatePattern, normalPattern)
                    example_object.encode_decode_txt()
                    print("not stuck 2")
                    email_chain, prev_date_pattern = example_object.filter_for_reply_dates(email_info_dict, recipient, prof_email)
                    print("not stuck3")

                    if prev_date_pattern:
                        reply_obj = example_object.look_for_date_in_msg(prev_date_pattern)
                        reply_dates_list.append(reply_obj)
                        print("not stuck4")
                    else:
                        continue


                    # look for the same subject line in the subject line list
                    # if it doesn;t exist, save the subject line in the list
                    # if it does, find which subject line has the more recent date
                    # then add up the conversations together


                    dialogue_style_email_list.append(email_chain)
                    print("not stuck5")


                    # find index
                    # there are no ">" for those emails

                # find an email in unique_group_email_list with that date, and delete it, since it'll just be a prev
                # response that we don't need to read through again. new_group_email_list = list(filter(lambda item:
                # item.get('date') != reply_obj, new_group_email_list))
                elif date_obj in reply_dates_list:
                    print("email has already been processed in a separate email thread. Looping to the next element...")
                    pass

    filtered_dia_list = []
    for one_dia in dialogue_style_email_list:
        prof_reply = False
        for element in one_dia:
            if "Professor:" in element:
                prof_reply = True
        if prof_reply:
            filtered_dia_list.append(one_dia)

    with open("sent_mail_2.json", "a") as outfile:
        json.dump(filtered_dia_list, outfile, indent=4)


mbox_file = "Sent.mbox"
sentDatePattern = r"\**(?:Date|Sent:)\**.*?\nTo:.*?.com"
normalPattern = r"\bOn\b.*?wrote:"
# normalPattern = r"\nOn\b [A-Za-z]{3,9}.*?wrote:"

prof_email = ["akang@ecornell.com", "ak16@cornell.edu"]

# parse_box(mbox_file, prof_email)
create_filtered_email_dialogue(prof_email)


