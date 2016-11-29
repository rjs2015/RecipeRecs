import scrapy
import pickle
from pymongo import MongoClient
from time import sleep
import re
client = MongoClient()
rx = re.compile(r'\w+\(([^\)]+)\)')
rdb = client.recipe_database_pt_2.rdb
revdb = client.recipe_reviews_pt_2.revdb

cursor = rdb.find()
recipe_tile_data = []

for i in range(rdb.count()):
    try:
        recipe_tile_data.append(dict(cursor.next()))
    except:
        pass

client.drop_database('recipe_database_pt_2')
rdb = client.recipe_database_pt_2.rdb

class RecipeSpider(scrapy.Spider):
	name = 'remaining_recipes'

	def start_requests(self):
		urls = ['http://allrecipes.com/' + j['link'] for j in recipe_tile_data]
		for url in urls:
			yield scrapy.Request(url=url, callback=self.parse)
			sleep(0.05)

	def parse(self, response):
		rdb.insert_one({
			'link': response.url.split('http://allrecipes.com/')[-1], 
			'ingredients': response.xpath('//span[@class="recipe-ingred_txt added"]/text()').extract(),
			'directions': response.xpath('//span[@class="recipe-directions__list--item"]/text()').extract(),
			'total_time': response.xpath('//span[@class="ready-in-time"]/text()').extract_first(),
			'made': rx.findall(response.xpath('//div[@class="total-made-it"]/@data-ng-init').extract_first())[0],
			'description':  response.xpath('//div[@class="submitter__description"]/text()').extract_first().strip()
			})
		for href in response.css('a.review-detail__link::attr(href)').extract():
			yield scrapy.Request(response.urljoin(href),
								 callback=self.parse_reviews)

	def parse_reviews(self, response):
		revdb.insert_one({
			'url': response.url.split('http://allrecipes.com/')[-1].split('reviews/')[0],
			'found_helpful': response.xpath('//div[@class="button helpful-count"]/format-large-number/@number').extract_first(),
			'stars': response.xpath('//div[@class="rating-stars"]/@data-ratingstars').extract_first(),
			'date': response.xpath('//div[@class="review-date"]/text()').extract_first(),
			'reviewer': response.xpath('//h4[@itemprop="author"]/text()').extract_first(),
			'followers': response.xpath('//ul[@class="cook-details__followers followers-count"]/li/span/format-large-number/@number').extract_first(),
			'favorites': response.xpath('//ul[@class="cook-details__favorites favorites-count"]/li/span/format-large-number/@number').extract_first(),
			'made': response.xpath('//ul[@class="cook-details__recipes-made recipes-made-count"]/li/span/format-large-number/@number').extract_first(),
			'review': response.xpath('//p[@itemprop="reviewBody"]/text()').extract_first()
		})
