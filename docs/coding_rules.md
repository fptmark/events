Here are rules for you to follow for the python server
	1. Follow clear seperation of concerns.  The architecture has a strict SoC and it must be followed.
	2. Do not mix python inheritance with code that uses pydantic.
	3. The routers are only an interface to the model and must not contain any model specific (except for the id if necessary) or database specific code.
	4. Common functions should reside in utils.py
	5. Main.py is responsible for startup and some generalized endpoint processing (swagger docs, metadata endpoint).
	6. The database should be swappable on startup via a config setting.  One affect is that the database id name cannot be pre-determined ("_id" or  "id") as it is database specific.  Therefore the id name and/or value can only be fetched via a function.
	7. Errors should be detected by the model (data validation, unique violations and missing fields).  Error messages should provide sufficient info so that it is obvious which id (for missing fields) and field caused as issue or which field did and what the error was.  The messages should be clear and handled in a highly consistant manner for processing by UI facing code.  Errors should also be logged and sent to the console.
	8. Follow DNR (do not repeat) unless it violates one of the above rules

Here are rules for the UI:
	1. SoC
	2. DNR
	3. Errors reporting from the UI or from the server should be handled in the same manner using the notification service.

Additional rules:
	1. Don't just patch code to mask a problem.  If a problem is encountered, figure out the root cause and if that.
	2. Don't create fallbacks that don't match the expected rules as it just hides problems.
	3. Do not create code for backwords compatibility.  There is no legacy system to support.

