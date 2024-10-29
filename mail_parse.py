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


def handleerror(errmsg, emailmsg, cs):
    print()
    print(errmsg)
    print("This error occurred while decoding with ",cs," charset.")
    print("These charsets were found in the one email.",getcharsets(emailmsg))
    print("This is the subject:",emailmsg['subject'])
    print("This is the sender:",emailmsg['From'])


def get_message_body(message):
    if message.is_multipart():
        for part in message.walk():
            if part.is_multipart():
                for subpart in part.walk():
                    if subpart.get_content_type() == 'text/plain':
                        # get subpart payload
                        body = subpart.get_payload(decode=True)
                    elif subpart.get_content_type() == 'html':
                        body_html = subpart.get_payload(decode=True)

    elif message.get_content_type() == 'text/plain':
        body = message.get_payload(decode=True)

    for charset in getcharsets(message):
        try:
            body = body.decode(charset)
        except UnicodeDecodeError:
            handleerror("UnicodeDecodeError: encountered.", message, charset)
        except AttributeError:
            handleerror("AttributeError: encountered", message, charset)
    return body


def parse_box(mbox_file):
    mbox = mailbox.mbox(mbox_file)

    # key = subject, value = list of dicts containing emails that has that subject line
    emails = {}
    for message in mbox:
        # message['Date'] = Thu, 11 Sep 2024 17:27:30 +0000
        # [5:-9] changes it to 11 Sep 2024 17:27

        message['Subject'] = message['Subject'].lower()
        # if subject line starts with "Re: " then remove it
        if message['Subject'].startswith('re: '):
            message['Subject'] = message['Subject'].replace('re: ', "")

        date_format = '%d %b %Y %H:%M'
        date_obj = datetime.strptime(message['Date'][5:-9], date_format)

        # find all the emails' subject lines and dates. we want to order all emails with the same subject by date.
        # find if subject already exists, and if so, add to existing list
        if message['Subject'] not in emails:
            body = get_message_body(message)
            emails[message['Subject']] = [{'from': message['From'], 'to': message['To'], 'date': date_obj, 'body': body}]
        elif message['Subject'] in emails:
            body = get_message_body(message)
            # this is a list of dictionaries
            new_list = emails[message['Subject']]
            new_list.append({'from': message['From'], 'to': message['To'], 'date': date_obj, 'body': body})
            emails[message['Subject']] = new_list

    dialogue_style_email_list = []

    for email_subject_key in emails:
        # retrieve the value of the key 'subject' from each dictionary
        # group_email_list is a list of dictionaries containing date, to, from, body information of emails
        group_email_list = emails[email_subject_key]
        # remove all the emails where it got an error decoding the body of the email and returned null
        group_email_list = list(filter(lambda item: item.get('body') == 'null', group_email_list))

        # remove dupes
        unique_group_email_list = []
        for d in group_email_list:
            if d not in unique_group_email_list:
                unique_group_email_list.append(d)

        # first sort emails by most recent
        unique_group_email_list = unique_group_email_list.sorted(key=lambda x: x['date'])

        reply_dates_list = []
        for email_info_dict in unique_group_email_list:
            if email_info_dict['date'] not in reply_dates_list:
                # we need to remove all the names from the emails.
                # first two elements are name of sender
                if list(email_info_dict['from'])[:1] == ["Abraham", "Kang"]:
                    student_name = list(email_info_dict['to'])[:1]
                else:
                    student_name = list(email_info_dict['from'])[:1]

                # retrieve body
                body = email_info_dict['body']

                hibye_list = ["hi", "hello",
                              "thanks", "regards", "my best",
                              "abe", "abraham", "kang", "--shellie"
                              "prof", "professor", "sir",
                              " , "]

                for _ in hibye_list:
                    # find and remove the greeting or sign off
                    body = body.replace(_, "")

                body = body.replace(student_name[0], "")
                body = body.replace(student_name[1], "")

                # look for the same subject line in the subject line list
                # if it doesn;t exist, save the subject line in the list
                # if it does, find which subject line has the more recent date
                # then add up the conversations together

                # if new line starts with "[image: "
                # remove that and everything after

                # turn all multi-spaces into 1 space and remove trailing spaces.
                ' '.join(body.split())

                # On Sun, Jan 3, 2021 at 5:44 PM [prev sender's name] <notifications@instructure.com>\nwrote:
                # look for specifically Jan 3, 2021 at 5:44 PM
                reply_date_pattern = r"\b([A-Za-z]{3}\s(\d{1,2}),\s(\d{4})\s([A-Za-z]{2}\s(\d{1,2}:\d{2})\s(AM|PM)\b"
                # returns list of all the indices it finds that pattern in the body, aka the quoted prev emails
                reply_indices = [match.start() for match in re.finditer(reply_date_pattern, body)]

                if reply_indices:
                    email_chain = []
                    counter = 0
                    # outputs all the matches
                    matches = re.findall(reply_date_pattern, body)
                    for date_index, match in zip(reply_indices, matches):
                        if reply_indices.index(date_index) != len(reply_indices) - 1:
                            one_email = body[:date_index - 1]
                            body = body[date_index:]

                            reply_date_format = '%b %d, %Y at %I:%M %p'
                            reply_obj = datetime.strptime(match, reply_date_format)

                            reply_dates_list.append(reply_obj)

                            # the very first quoted email sometimes have an automated part that says
                            # "You can reply to this message on blah blah" and so remove everything after that

                        elif reply_indices.index(date_index) == len(reply_indices) - 1:
                            one_email = body[:]
                            trailing_deletions = ["[image: ", "You can reply to this message", "Sent from my"]
                            for one_trailing in trailing_deletions:
                                if one_trailing in one_email:
                                    one_email = one_email[:one_email.index(one_trailing) - 1]

                        if counter != 0:
                            string_to_delete = ">" * counter
                            string_to_delete = "\n" + string_to_delete + " "
                            one_email.replace(string_to_delete, "")

                        email_chain.append(one_email)
                        counter = counter + 1
                    dialogue_style_email_list.append(email_chain)
                # it doesn't have replies, ie it's just one message
                elif not reply_indices:
                    # not worth trying to figure it out lmao
                    pass

                # find index
                # there are no ">" for those emails

            # find an email in unique_group_email_list with that date, and delete it, since it'll just be a prev
            # response that we don't need to read through again. new_group_email_list = list(filter(lambda item:
            # item.get('date') != reply_obj, new_group_email_list))
            elif email_info_dict['date'] in reply_dates_list:
                pass

    for one_dialogue_chain in dialogue_style_email_list:
        with open("sent_mail_2.json", "a") as outfile:
            json.dump(one_dialogue_chain, outfile, indent=4)


mbox_file = "Sent.mbox"
parse_box(mbox_file)
