import configparser
import json
import os
from datetime import datetime, timedelta

from webnotes.ConfluencePageNodes import ParagraphNode
from webnotes.ConfluencePageNodes.InlineExtensionNode import InlineExtensionNode
from webnotes.ConfluencePageNodes.Table import TableNode
from webnotes.ConfluencePageNodes.TextContent import TextContent
from .InlineCardNode import InlineCardNode
from .PanelNode import PanelNode
from .HeadingNode import HeadingNode
from .ExtensionNode import ExtensionNode
from .RootNode import RootNode
from .Table.BulletListNode import BulletListNode
from .. import utilities, JiraInterface

def init_config():
    # Read configuration from config.ini
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), os.path.pardir, 'config.ini'))
    space_id = config.get('CONF', 'spaceId')
    author_id = config.get('CONF', 'authorId')
    review_parent_id = config.get('CONF', 'review_parentId')
    onetoone_parent_id = config.get('CONF', 'onetoone_parentId')
    return space_id, author_id, review_parent_id, onetoone_parent_id


def get_review_table():
    table_data = JiraInterface.get_finish_sprint_table_data()
    table_data.sort(key=lambda issue: (issue.parent_topic is None, issue.parent_topic or ""))

    table_node = TableNode(5, [568.0, 122.0, 722.0, 191.0, 197.0])
    table_node.add_title_row(["Jira Issue", "Topic / Epic", "Daten / Kommentar", "Reporter", "Assignee"])

    for row in table_data:
        table_node.add_jira_table_row(row)

    return table_node


def get_1to1_table_data():
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), os.path.pardir, 'config.ini'))
    ep_link = config.get('CONF', 'ep_link')


    rows = []
    bullet_list_node1 = BulletListNode(["Bist du zufrieden mit deiner Leistung seit dem letzten 1:1?", "Hast du deiner Meinung nach genügend zum Erfolg des Teams beigetragen?"])
    empty_paragraph_node = ParagraphNode(TextContent.create_empty())
    rows.append([bullet_list_node1, empty_paragraph_node])

    paragraph_node2 = ParagraphNode(TextContent('Worüber hast du dich in den vergangenen 4 Wochen am meisten gefreut, bzw. geärgert (Beruf und/oder Privat)?'))
    rows.append([paragraph_node2, empty_paragraph_node])

    paragraph_node3 = ParagraphNode(TextContent('Gab es in den vergangenen 4 Wochen Überraschungen/Unerwartetes?'))
    rows.append([paragraph_node3, empty_paragraph_node])

    paragraph_node4 = ParagraphNode(TextContent('Gibt es etwas was dich beschäftigt und nicht im Team besprochen werden kann?'))
    rows.append([paragraph_node4, empty_paragraph_node])

    paragraph_node5 = ParagraphNode(TextContent('Kann ich dich bei etwas unterstützen?'))
    rows.append([paragraph_node5, empty_paragraph_node])

    paragraph_node6 = ParagraphNode(TextContent('Entwicklungsplan'))
    link_node = InlineCardNode(ep_link)
    rows.append([paragraph_node6, link_node])

    paragraph_node7 = ParagraphNode(TextContent('TL-Feedback'))
    rows.append([paragraph_node7, empty_paragraph_node])

    paragraph_node8 = ParagraphNode(TextContent('weiteres (nach Bedarf)'))
    rows.append([paragraph_node8, empty_paragraph_node])

    return rows

def get_1to1_table():
    table_data = get_1to1_table_data()
    table_node = TableNode(2, [834.0, 966.0])

    for row in table_data:
        table_node.add_table_row(row)

    return table_node


def create_review_body():
    intro_panel = PanelNode(
        panelType="note",
        content=HeadingNode(
            level=1,
            text="Ziel Review: Wohin entwickeln sich unsere Produkte kurz- und mittelfristig?"
        )
    )

    toc_extension = ExtensionNode.get_toc_extension()

    heading_weiterentwicklung = HeadingNode(
        level=1,
        text="Weiterentwicklung Produkte Phoenix (20min)"
    )

    heading_focus = HeadingNode(
        level=3,
        text="Focus"
    )

    paragraph_inis_node = ParagraphNode(content=InlineExtensionNode.get_upcoming_phx_initiatives())

    heading_sprint = HeadingNode(
        level=2,
        text="Übersicht abgeschlossener Sprint"
    )

    paragraph_space_node = ParagraphNode(content=TextContent(" "))

    table_node = get_review_table()

    jira_os_extension = ExtensionNode.get_jira_filter_extension(
        "Team[Team] = 26 AND Sprint in openSprints()  ORDER BY Rank ASC")

    heading_next = HeadingNode(
        level=2,
        text="Übersicht nächste Sprints"
    )

    jira_fs_extension = ExtensionNode.get_jira_filter_extension(
        "Team[Team] = 26 AND Sprint in futureSprints()  ORDER BY Sprint ASC")

    content = [intro_panel, toc_extension, heading_weiterentwicklung, heading_focus, paragraph_inis_node,
               heading_sprint, paragraph_space_node, table_node, jira_os_extension, heading_next,
               jira_fs_extension]

    # Create a root node that contains the panel
    root = RootNode(
        content=content,
        version=1
    )

    return root

def create_review_page():
    space_id, author_id, review_parent_id, _ = init_config()
    title = get_review_title()
    status = "current"

    # Create the body of the review page
    body = create_review_body()

    return ConfluencePage(
        title=title,
        authorId=author_id,
        parentId=review_parent_id,
        body=body,
        spaceId=space_id,
        status=status
    )


def create_1to1_body():
    one_to_one_table = get_1to1_table()

    content = [one_to_one_table]

    # Create a root node that contains the panel
    root = RootNode(
        content=content,
        version=1
    )

    return root


def create_1to1_page():
    space_id, author_id, _, one_to_one_parent_id = init_config()
    title = get_1to1_title()
    status = "current"

    # Create the body of the review page
    body = create_1to1_body()

    return ConfluencePage(
        title=title,
        authorId=author_id,
        parentId=one_to_one_parent_id,
        body=body,
        spaceId=space_id,
        status=status
    )

def get_review_title():
    sprint_number = utilities.get_current_sprint()
    start_date, end_date = utilities.get_start_end_date()
    # Format dates as DD.MM.YYYY
    formatted_start = start_date.strftime('%d.%m.%Y')
    formatted_end = end_date.strftime('%d.%m.%Y')
    return f'Sprint {sprint_number} Review ({formatted_start} - {formatted_end})'

def get_1to1_title():    
    # Get today's date
    today = datetime.now()
    
    # Calculate days until next Thursday (where Monday is 0 and Sunday is 6)
    days_until_thursday = (3 - today.weekday()) % 7
        
    # Calculate the date of the next Thursday
    next_thursday = today + timedelta(days=days_until_thursday)
    
    # Format date as YYYY-MM-DD
    formatted_date = next_thursday.strftime('%Y-%m-%d')
    
    return f"{formatted_date} Srdjan/Dominic"


class ConfluencePage:
    def __init__(self, title, authorId, parentId, body, spaceId, status="current"):
        self.title = title
        self.authorId = authorId
        self.parentId = parentId
        self.body = body  # Should be RootNode
        self.spaceId = spaceId
        self.status = status

    def to_json(self):
        body_dict = self.body.to_json()
        body_string = json.dumps(body_dict).replace('"', '\"')
        review_page_dict = {
            'title': self.title,
            'authorId': self.authorId,
            'parentId': self.parentId,
            'body': {'atlas_doc_format': {'representation': 'atlas_doc_format', 'value': body_string}},
            'spaceId': self.spaceId,
            'status': self.status
        }
        return json.dumps(review_page_dict)
