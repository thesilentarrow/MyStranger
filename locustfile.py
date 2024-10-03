from locust import HttpUser, between, task

class MyUser(HttpUser):

    @task
    def connect_to_websocket(self):
        self.client.get("/")

    @task
    def connect_to_websocket1(self):
        self.client.get("/new_chat/")
    @task
    def connect_to_websocket2(self):
        self.client.get("/new_chat_text/")
    @task
    def connect_to_websocket3(self):
        self.client.get("/account/18/")
    # @task
    # def connect_to_websocket4(self):
    #     self.client.get("/vibes/")
    @task
    def connect_to_websocket5(self):
        self.client.get("/chat/")
    @task
    def connect_to_websocket5(self):
        self.client.get("/nrt_text/")

    # Add more tasks as needed

