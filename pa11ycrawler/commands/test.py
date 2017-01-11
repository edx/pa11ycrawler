from scrapy.commands.crawl import Command as ExistingCrawlCommand
from scrapy.exceptions import UsageError
from pa11ycrawler.spiders.edx import EdxSpider

class Command(ExistingCrawlCommand):

    requires_project = True

    def short_desc(self):
        return 'Run a spider that fails on specified errors'

    def run(self, args, opts):
        if len(args) < 1:
            raise UsageError()
        elif len(args) > 1:
            raise UsageError("running 'scrapy crawl' with more than one spider is no longer supported")
        spname = args[0]

        self.crawler_process.crawl(spname, **opts.spargs)
        crawler = list(self.crawler_process.crawlers)[0]
        self.crawler_process.start()

        for setting in crawler.settings['FAILURE_CATEGORIES']:
            if crawler.stats.get_value(setting, 0) > 0:
                self.exitcode = 1
