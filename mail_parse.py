import mailbox
import json
from datetime import datetime
import re


def getcharsets(msg):
    charsets = set({})
    for c in msg.get_charsets():
        if c is not None:
            charsets.update([c])
    return charsets


# def handleerror(errmsg, emailmsg, cs):
# print()
# print(errmsg)
# print("This error occurred while decoding with ", cs, " charset.")
# print("These charsets were found in the one email.", getcharsets(emailmsg))
# print("This is the subject:", emailmsg['subject'])
# p rint("This is the sender:", emailmsg['From'])


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
    return msg_body


def parse_box(mbox_file):
    mbox = mailbox.mbox(mbox_file)
    emails = {}
    prof_email = ["akang@ecornell.com", "ak16@cornell.edu"]
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
        match_date_str = re.search(r'\d{1,2}\s[A-Za-z]{3}\s\d{4}\s\d{2}:\d{2}:\d{2}\s[+-]\d{4}', message['Date'])
        date_format = '%d %b %Y %H:%M:%S %z'
        date_obj = datetime.strptime(match_date_str.group(), date_format)
        email_dict.update({'Date': date_obj})

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
    dialogue_style_email_list = []
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
        print("filtering datetime objects in date keys")

        reply_dates_list = []
        for email_info_dict in group_email_list:
            print("opening dictionary of emails that have the same subject line.")
            print(email_info_dict)

            if email_info_dict['Date'] not in reply_dates_list:
                print("this email has not yet been processed/is a new email thread, as there it shares no same date "
                      "as another email. Processing:")
                print("\n")
                # we need to remove all the names from the emails.
                # first two elements are name of sender

                # retrieve body
                body = email_info_dict['Body']

                hibye_list = ["hi", "hello",
                              "thanks", "regards", "my best",
                              "best", "dear",
                              "abe", "abraham", "kang",
                              "mr", "prof", "professor", "sir",
                              "akang@ecornell.com", "ak16@cornell.edu"]

                ls_recipient = email_info_dict['recipient'].split()

                suffix = ["I", "II", "III", "IV", "Jr.", "Sr."]
                if any(item in ls_recipient[-1] for item in suffix):
                    # concatenate second to last element + suffix
                    # so when removing the suffix it won't remove things like
                    # "Part III" to "Part " in the email
                    ls_recipient[len(ls_recipient)-2] = ' '.join(ls_recipient[len(ls_recipient) - 2], ls_recipient[-1])
                print(ls_recipient)
                hibye_list.extend(ls_recipient)

                hibye_list = [rf"\b{_}\b" for _ in hibye_list]
                hibye_list.extend([r"--\b", r"(\n+|\s+)(\.|,)", r"^(\n*|\s*)(,|\.)"])

                # greet_pattern = re.compile("|".join(new_hibye_list), re.IGNORECASE)
                # no_greet_body = greet_pattern.sub('', body)
                # print(no_greet_body)

                # above doesn't work. since it does it concurrently, it doesnt delete the " . " that's left
                # after removing "mr". so i have to do it in a loop. so i do that below.

                for _ in hibye_list:
                    # find and remove the greeting or sign off
                    print(f"filtering for {_}")

                    body = re.sub(_, '', body, flags=re.IGNORECASE)
                print(body)

                print("email body is removed of greetings and names")

                # look for the same subject line in the subject line list
                # if it doesn;t exist, save the subject line in the list
                # if it does, find which subject line has the more recent date
                # then add up the conversations together

                # if new line starts with "[image: "
                # remove that and everything after

                # turn all multi-spaces into 1 space and remove trailing spaces.
                # ' '.join(body.split())

                # both patterns exist in mbox file (most likely some kind of external email quote or that the mbox format
                # was updated at some point
                # On Sun, Jan 3, 2021 at 5:44 PM [prev sender's name] <notifications@instructure.com>\nwrote:
                # On Sun, Jan 3, 2021, 5:44 PM [prev sender's name] <notifications@instructure.com>\nwrote:
                # .*? (question mark important, otherwise it will match everything starting from "On x date" and on
                # ?s meaning line breaks like \n is also included
                reply_date_pattern = r"On [A-Za-z]{3}, [A-Za-z]{3} \d{1,2}, \d{4}\s*(at|,) \d{1,2}:\d{2} (AM|PM)(?s).*?wrote:"
                # returns list of all the indices it finds that pattern in the body, aka the quoted prev emails

                reply_matches = re.finditer(reply_date_pattern, body)
                print("got this far")

                match_group = [match.group() for match in reply_matches]

                # it doesn't have replies, ie it's just one message
                if not match_group:
                    # not worth trying to figure it out lmao
                    print("no reply matches found")
                    pass

                elif match_group:
                    counter = 0

                    print("quoted email history found in email. Processing:")
                    print(match_group)

                    email_chain = []
                    # beginning_deletions = [r"show quoted text (?s).*>"]
                    while counter <= len(match_group):
                        one_email = body
                        if counter < len(match_group):
                            if " at " in match_group[counter]:
                                reply_date_format = 'On %a, %b %d, %Y at %I:%M %p'
                            else:
                                reply_date_format = 'On %a, %b %d, %Y, %I:%M %p'
                            # this matches anything after AM or PM (? <=[AM | PM]). *
                            # but instead, i match up to AM and PM, then with r'1' i include the AM/PM from
                            # the capture group to be included in the new string
                            # match anything after AM or PM
                            match_group_dt_format = re.sub(r"(?<=AM|PM)(?s).*", '', match_group[counter])
                            reply_obj = datetime.strptime(match_group_dt_format, reply_date_format)
                            # so that while iterating through the for loop, if i come across emails that have these exact dates,
                            # i don't process them again. and since i already sorted the list of emails based on the most recent
                            # dates, i'll be processing the ones that are the most recent first.
                            reply_dates_list.append(reply_obj)

                            index = body.find(match_group[counter])
                            end_index = -1
                            if index != -1:
                                end_index = index + len(match_group[counter])
                            print("Match found: ", match_group[counter])
                            print("Start index: ", index)
                            print("End index: ", end_index)

                            one_email = body[:index - 1]
                            body = body[end_index + 1:]

                            # counter == 0 it is still at the most top/recent email, before the quote history.
                            # for the most recent email, find who wrote it based on who sent it using to_student.
                            if counter == 0:
                                # if to_student is True, it means email was sent from professor to student.
                                if email_info_dict['to_student']:
                                    email_header = 'Professor'
                                else:
                                    email_header = 'Student'
                            # otherwise find who wrote the email based on the reply_matches pattern, and extract the
                            # name from that.
                            else:
                                # why was i trying to find the regex match for the exact name???? i spent so much time for no reason
                                # just check whether professor's name/email is in the match_group[counter]
                                # email_header = re.search(r"(?<=AM|PM)(?s).*(?=\s*<(?s).*?wrote:)", match_group[counter])
                                if any(item in match_group[counter] for item in prof_email):
                                    email_header = 'Professor'
                                else:
                                    email_header = 'Student'

                        # i dont want to delete code that maybe is using the ">" expression, so im being specific
                        quote_string = "\n" + ("> " * counter)

                        # delete the longer > > sequence first so its less of a headache
                        quote_search = re.search(r"show quoted text <(?s).*_>", one_email, re.IGNORECASE)
                        if quote_search:
                            print("found show quoted texted message in email. removing:")
                            one_email = re.sub(r"show quoted text <(?s).*_>", '', one_email)
                            print(one_email)
                            # add one more > and then delete those
                            extra_quote_string = quote_string + "> "
                            if extra_quote_string in one_email:
                                print("found extra >. removing")
                                one_email.replace(extra_quote_string, "")
                                print(one_email)

                            if quote_string in one_email:
                                print("found quoted text. removing")
                                one_email.replace(quote_string, "")

                            print("removed!")

                        trailing_deletions = ["Sent from my", "[image: ", "You can reply to this message",
                                              "The contents of this email are the property of PNC. If it was not "
                                              "addressed to you, you have no legal right to read it."]
                        # after the loop body has been removed down to the first email in the quoted reply history
                        for one_trailing in trailing_deletions:
                            if one_trailing in one_email:
                                print("found trailing messages/links from Canvas to delete. Deleting...")
                                one_email = one_email.split(one_trailing)[0]

                        one_email = f"{email_header}:\n{one_email}"
                        print(f"\n\nONE EMAIL:\n{one_email}\n\n")
                        print(f"\n\nREST OF BODY WITHOUT ONE EMAIL:\n{body}\n\n")

                        email_chain.append(one_email)
                        counter += 1

                        # the very first quoted email sometimes have an automated part that says
                        # "You can reply to this message on blah blah" and so remove everything after that

                    dialogue_style_email_list.append(email_chain)

                # find index
                # there are no ">" for those emails

            # find an email in unique_group_email_list with that date, and delete it, since it'll just be a prev
            # response that we don't need to read through again. new_group_email_list = list(filter(lambda item:
            # item.get('date') != reply_obj, new_group_email_list))
            elif email_info_dict['date'] in reply_dates_list:
                print("email has already been processed in a separate email thread. Looping to the next element...")
                pass

    for one_dialogue_chain in dialogue_style_email_list:
        print("GOT TO THE EMAIL DIALOGUE")
        for email in one_dialogue_chain:
            print("\n----------\nDIVIDE BETWEEN EMAILS\n------------")
            print(email)

        with open("sent_mail_2.json", "a") as outfile:
            json.dump(one_dialogue_chain, outfile, indent=4)


mbox_file = "Sent.mbox"
parse_box(mbox_file)
