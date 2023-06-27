# Todo

1. Update recommendation to intelligently look through comments and pick relevant ones to use for recommendation.
2. Relevancy Percentage update with text 50%, 70% instead of changing in code
3. 
4. 

## Setup

To install the required packages for this plugin, run the following command:

```bash
pip install -r requirements.txt
```

Create a keys.py file and put the below code with your OpenAI key inside:

```
openai_key = "sk-************"
```

To run the plugin, enter the following command:

```bash
python main.py
```

Once the local server is running:

1. Navigate to https://chat.openai.com. 
2. In the Model drop down, select "Plugins" (note, if you don't see it there, you don't have access yet).
3. Select "Plugin store"
4. Select "Develop your own plugin"
5. Enter in `localhost:5003` since this is the URL the server is running on locally, then select "Find manifest file".

The plugin should now be installed and enabled! You can start with a question like "What is on my todo list" and then try adding something to it as well! 

## Getting help

If you run into issues or have questions building a plugin, please join our [Developer community forum](https://community.openai.com/c/chat-plugins/20).
