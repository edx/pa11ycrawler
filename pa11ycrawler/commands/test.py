"""
Contains the scrapy test command for configurable process failures.
"""
from scrapy.commands import ScrapyCommand
from scrapy.commands.crawl import Command as ExistingCrawlCommand


class Command(ScrapyCommand):
    """
    A wrapper for scrapy crawl that assigns the process a nonzero exit code if
    any errors are raised during execution. Error categories are configurable
    via settings['FAILURE_CATEGORIES']. It wraps, rather than extends, the
    existing crawl command so it can be tested in isolation.
    """
    requires_project = True
    existing_crawl_command = ExistingCrawlCommand()

    def syntax(self):
        return '[options] <spider>'

    def short_desc(self):
        return 'Run a spider that fails on specified errors'

    def add_options(self, parser):
        self.existing_crawl_command.settings = self.settings
        self.existing_crawl_command.add_options(parser)

    def process_options(self, args, opts):
        self.existing_crawl_command.process_options(args, opts)

    def run(self, args, opts):
        spname = args[0]

        crawler = self.crawler_process.create_crawler(spname)
        self.existing_crawl_command.crawler_process = self.crawler_process
        self.existing_crawl_command.run(args, opts)

        for setting in crawler.settings['FAILURE_CATEGORIES']:
            if crawler.stats.get_value(setting, 0):
                self.exitcode = 1
                break
