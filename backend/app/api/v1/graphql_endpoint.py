import strawberry
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello from APICred GraphQL API!"

schema = strawberry.Schema(query=Query)

router = GraphQLRouter(schema)
