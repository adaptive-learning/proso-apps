from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse


class MapSitemap(Sitemap):
    def location(self, item):
        return '/#/view/' + item.code + '/'


class FlatPages(Sitemap):
    locations = {
        'about': '/#/about',
        'how-it-works': '/#/how-it-works',
        'world': '/#/view/world/',
    }

    def priority(self, item):
        return 1 if item == "home" else 0.8

    def items(self):
        return ['home', 'about', 'how-it-works', 'world']

    def location(self, item):
        return self.locations[item] if item in self.locations else reverse(item)


sitemaps = {
    'flatpages': FlatPages,
}
