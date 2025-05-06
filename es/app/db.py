from elasticsearch import AsyncElasticsearch


class Database:
    _es_client: AsyncElasticsearch | None = None
    _es_url: str = ""
    _es_dbname: str = "" 

    @staticmethod
    async def init(url: str, dbname: str): 
        Database._es_url = url
        Database._es_dbname = dbname
        Database._es_client = AsyncElasticsearch(hosts=[Database._es_url])


    @staticmethod
    def get_es_client() -> AsyncElasticsearch | None:
        return Database._es_client