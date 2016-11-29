import scrapy
import pickle
from pymongo import MongoClient
from time import sleep
import requests
from bs4 import BeautifulSoup
client = MongoClient()
tiledb = client.recipe_tiles.tiledb

# A scraper to grab recipe tiles from allrecipes.com category pages

url = 'http://allrecipes.com/recipes/?grouping=all'
response = requests.get(url)
page = response.text
page = BeautifulSoup(page, 'lxml')

pages = {('http://allrecipes.com' + i['href'] if 'http:' not in i['href'] else i['href']):i['title']
         for i in page.findAll("a", {"class":"hero-link__item"})}
pages['http://allrecipes.com/recipes/17235/everyday-cooking/allrecipes-magazine-recipes/'] = 'Magazine Favorites Recipes' 

class RecipeSpider(scrapy.Spider):
	name = 'tiles'

	def start_requests(self):
		urls = sum([[j+"?page="+str(k) for k in range(1,500)] for j in pages.keys()], [])
		for url in urls:
			yield scrapy.Request(url=url, callback=self.parse)
			sleep(0.05)

	def parse(self, response):
		# follow links to review pages
		for i in response.xpath('//article[@class="grid-col--fixed-tiles"]'):
			tiledb.insert_one({
				'cat': pages[response.url.split('?page')[0]],
				'title': i.xpath('.//h3/text()').extract_first().strip(),
				'review_count': i.xpath('.//span[@class="grid-col__reviews"]/format-large-number/@number').extract_first(),
				'rating': i.xpath('.//div[@class="rating-stars"]/@data-ratingstars').extract_first(),
				'desc': i.xpath('.//div[@class="rec-card__description"]/text()').extract_first().strip(),
				'author': i.xpath('.//h4/text()').extract_first().strip(),
				'link': i.xpath('.//a/@href').extract_first()
			})

