import re
from datetime import datetime

import quopri


class EmailClass:
    def __init__(self, date, msg_from, to, body, to_student, sentDatePattern, normalPattern):
        self.date = date
        self.msg_from = msg_from
        self.to = to
        self.body = body
        self.to_student = to_student
        self.sentDatePattern = sentDatePattern
        self.normalPattern = normalPattern

    def __str__(self):
        return f"example string representation of EmailClass is {self.date} ({self.age})"

    def encode_decode_txt(self):
        try:
            quopri.decodestring(self.body)
        except Exception:
            pass
        try:
            self.body.encode('ascii', 'ignore').decode('utf-8')
        except Exception:
            pass

    def look_for_date_in_msg(self):
        match_date_str = re.search(r'\d{1,2}\s[A-Za-z]{3}\s\d{4}\s\d{2}:\d{2}:\d{2}\s[+-]\d{4}', self.date)

        date_format = '%d %b %Y %H:%M:%S %z'
        date_obj = datetime.strptime(match_date_str.group(), date_format)

        return date_obj

    def delete_quote_symbol(self):
        # delete all quote histroy patterns in all of the body.

        # \n(?:(?:>\s)*)
        self.body = self.body.replace("\n> ", "\n")
        self.body = self.body.replace("\n>", "\n")

        show_quoted_text_str = re.search(r"show quoted text <(?s:).*?_>", self.body, re.IGNORECASE)
        if show_quoted_text_str:
            self.body = re.sub(r"show quoted text <(?s:).*?_>", '', self.body)
        return self.body

    """def find_dates_of_replies(self):
        reply_matches = re.finditer(self.reply_date_pattern, body, re.DOTALL)
        match_group = [match.group().encode('ascii', 'ignore').decode('utf-8') for match in reply_matches]
        return match_group
    """
    def find_who_from(self, prev_match, prof_name_and_email_list):
        if any(item in prev_match for item in ["Sent:", "Date:"]):
            who_from = re.search(r"(?<=From:).*?(?=\n*>*\s*\**Sent:.*?)", prev_match).group()
            who_from = who_from.replace("*", "")
        else:
            prev_match = prev_match.replace(" wrote:", "")
            who_from = re.search(r"(?<=AM|PM)(?s:).*", prev_match).group()

        name_sign_offs = who_from.split()[:-1]

        if any(item in who_from for item in prof_name_and_email_list):
            email_header = 'Professor'
        else:
            email_header = 'Student'
            # only save up to second last element. last element = email.
            # pretend there are no suffixes. but there are suffixes. so..yeah.

        return name_sign_offs, email_header

    def remove_sign_offs(self, part_of_reply, name_sign_offs, email_header):
        for one_name in name_sign_offs:
            potential_sign_off_str = f"\n{one_name}"
            # if sender repeats their own name after a newline, delete it. most likely signature.
            match = re.search(potential_sign_off_str, part_of_reply, re.IGNORECASE)
            if match:
                part_of_reply = part_of_reply[:match.start() - 1]
                # print('removed potential sign off')

        trailing_deletions = ["Sent from my", "[image: ", "You can reply to this message",
                              "The contents of this email are the property of PNC. If it was not "
                              "addressed to you, you have no legal right to read it."]
        # after the loop body has been removed down to the first email in the quoted reply history
        for one_trailing in trailing_deletions:
            one_trailing = re.escape(one_trailing)
            match = re.search(one_trailing, part_of_reply, re.IGNORECASE)
            if match:
                # print("found trailing messages/links from Canvas to delete. Deleting...")
                part_of_reply = part_of_reply[:match.start() - 1]

        part_of_reply = f"{email_header}: {part_of_reply}"
        part_of_reply = re.sub(r'\n+', '\n', part_of_reply)
        part_of_reply.rstrip()
        return part_of_reply

    def filter_for_reply_dates(self):
        prev_match = ""
        email_header = ""
        email_chain = []
        counter = 0
        lastEmail = False

        reply_date_pattern = rf"({self.sentDatePattern})|({self.normalPattern})"
        while not lastEmail:
            if re.search(reply_date_pattern, self.body, re.DOTALL):
                if any(item in re.search(reply_date_pattern, self.body, re.DOTALL).group() for item in ["Sent", "Date"]):
                    complete_pattern = r"\**From:.*?(Subject:.*just sent you a message in Canvas\.)"
                else:
                    complete_pattern = self.normalPattern

                complete_match_to_remove = re.search(complete_pattern, self.body, re.DOTALL)

                complete_match_index = complete_match_to_remove.start()
                complete_match_end = complete_match_to_remove.end()

                # print("Match found: ", complete_match_to_remove.group())
                # print("Start index: ", complete_match_index)
                # print("End index: ", complete_match_end)

                one_email = self.body[:complete_match_index - 1]
                # print("one email is the email BEFORE the matched reply format")
                self.body = self.body[complete_match_end + 1:]

                # counter == 0 it is still at the most top/recent email, before the quote history.
                # for the most recent email, find who wrote it based on who sent it using to_student.
                if counter == 0:
                    # if to_student is True, it means email was sent from professor to student.
                    if email_info_dict['to_student']:
                        email_header = 'Professor'
                        name_sign_offs = ['Abe', 'Abraham', 'Kang']
                    else:
                        email_header = 'Student'
                        name_sign_offs = recipient.split()
                        # in real parser, make sure to check for suffixes.

                # otherwise find who wrote the email based on the reply_matches pattern, and extract the name
                # from that. why was i trying to find the regex match for the exact name???? i spent so much
                # time for no reason just check whether professor's name/email is in the match_group[counter]
                # email_header = re.search(r"(?<=AM|PM)(?s).*(?=\s*<(?s).*?wrote:)", match_group[counter])
                elif counter > 0:
                    name_sign_offs, email_header,  = self.find_who_from(prev_match, prof_name_and_email_list)

                one_email = self.remove_sign_offs(one_email, name_sign_offs, email_header)
                counter += 1

                email_chain.append(one_email)

                prev_match = complete_match_to_remove.group()

            elif not re.search(reply_date_pattern, self.body, re.DOTALL):
                name_sign_offs, email_header = self.find_who_from(prev_match, prof_name_and_email_list)
                lastEmail = self.remove_sign_offs(self.body, name_sign_offs, email_header)

                email_chain.append(lastEmail)



        return email_chain


date = "Mon, 16 Sep 2019 07:39:58 -0700"
to = "Brian Kane <bkane@collegeave.com>"
msg_from = "Abraham Kang ak16@cornell.edu"
body = "Ok.\n\nRegards,\nAbe\n\nOn Mon, Sep 16, 2019 at 5:18 AM Brian Kane <bkane@collegeave.com> wrote:\n\n> Sorry " \
       "for the delay.  I\u2019ll have it turned in by end of day today.\n>\n>\n>\n> Brian Kane\n>\n> Head of Pricing " \
       "Strategy\n>\n>\n>\n> College Ave Student Loans\n>\n> 233 N. King St. Suite 400\n> Wilmington, DE 19801\n>\n> " \
       "C: 610-883-2969\n>\n> bkane@collegeave.com\n>\n>\n>\n>\n>\n> CONFIDENTIALITY NOTICE:  This electronic mail " \
       "transmission may contain\n> information that is confidential, privileged, proprietary, or otherwise\n> " \
       "legally exempt from disclosure. If you are not the intended recipient, you\n> are hereby notified that you " \
       "are not authorized to read, print, retain,\n> copy or disseminate this message, any part of it, " \
       "or any attachments. If\n> you have received this message in error, please delete this message and any\n> " \
       "attachments from your system without reading the content and notify the\n> sender immediately of the " \
       "inadvertent transmission. There is no intent on\n> the part of the sender to waive any privilege, " \
       "including the\n> attorney-client privilege, that may attach to this communication. Thank you\n> for your " \
       "cooperation.\n>\n>\n>\n> *From:* Abraham Kang <notifications@instructure.com>\n> *Sent:* Sunday, " \
       "September 15, 2019 12:06 AM\n> *To:* Brian Kane <bkane@collegeave.com>\n> *Subject:* Abraham Kang (Debugging " \
       "and Improving Machine Learning Models)\n> just sent you a message in Canvas.\n>\n>\n> No submission for " \
       "Gradient Boosted Regression Tree\n>\n> The class ends Tues. Please get this assignment turned in.\n>\n> Send " \
       "me an email at akang@ecornell.com if you need help.\n>\n> Regards,\n> Abe\n>\n>\n>\n> [image: Abraham " \
       "Kang]\n>\n> *Abraham Kang*\n>\n> You can reply to this message in Canvas by replying directly to this\n> " \
       "email. If you need to include an attachment, please log in to Canvas and\n> reply through the " \
       "Inbox.\n>\n>\n>\n>\n>\n> View this message in Conversations\n> " \
       "<https://lms.ecornell.com/conversations/8224438> |  Update your\n> notification settings " \
       "<https://lms.ecornell.com/profile/communication>\n>\n>\n>\n"

to_student = True
sentDatePattern = r"\**(Date|Sent:)\**.*?(AM|PM)"
normalPattern = r"\nOn.* ?wrote:"

example_object = EmailClass(date, msg_from, to, body, to_student, sentDatePattern, normalPattern)
example_object.encode_decode_txt()

date_obj = example_object.look_for_date_in_msg()
body = example_object.delete_quote_symbol()

email_info_dict = {'to_student': to_student}
email_info_dict.update({'Date': date_obj})

recipient = to
prof_name_and_email_list = ["Abe", "Abraham", "Kang", "akang@ecornell.com", "ak16@cornell.edu"]


# define match_group after deleting quotes, so that match_group also no longer has quotes and it matches its duplicate.`
email_chain = example_object.filter_for_reply_dates()
print(email_chain)
'''
reply_date_format = '%a, %b %d, %Y %I:%M %p'
if ", at " in match_group[counter]:
    match_group_dt_format = match_group_dt_format.replace('On ', '').replace(', at ', ' ').strip()
elif " at " in match_group[counter]:
    match_group_dt_format = match_group_dt_format.replace('On ', '').replace(' at ', ' ').strip()
elif "Sent:" in match_group[counter]:
    match_group_dt_format = match_group[counter].replace('Sent:', '').strip()
    if "*" in match_group[counter]:
        match_group_dt_format = match_group_dt_format.replace('*', '').strip()
    reply_date_format = '%A, %B %d, %Y %I:%M %p'
    notSentOrDate = False
elif "Date:" in match_group[counter]:
    match_group_dt_format = match_group[counter].replace('Date:', '').strip()
    if "*" in match_group[counter]:
        match_group_dt_format = match_group_dt_format.replace('*', '').strip().rstrip(',')
    notSentOrDate = False
else:
    match_group_dt_format = match_group[counter].replace('On ', '').strip().rstrip(',')

reply_obj = datetime.strptime(match_group_dt_format, reply_date_format)
'''
