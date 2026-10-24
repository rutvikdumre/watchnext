# watchnext
watchNext is a movie recommendation website. ranzol, its recommender, matches movies by cast, crew, genre and more, and live movie data comes from IMDb.
<hr>
<h3>Deploy</h3>
One-click deploy on Render (free plan) using <code>render.yaml</code>: <a href="https://render.com/deploy?repo=https://github.com/rutvikdumre/watchnext">Deploy to Render</a>
<br>
<h3>Keeping data (accounts and shared watchlists)</h3>
Render's free plan wipes the disk on every restart, so give the app a free Postgres database:
<ol>
<li>Create a free project at <a href="https://neon.tech">neon.tech</a> and copy its connection string (<code>postgresql://…?sslmode=require</code>).</li>
<li>In Render: your service → <b>Environment</b> → add <code>DATABASE_URL</code> with that value → Save. Render redeploys and creates the tables.</li>
</ol>
<h3>To run it locally:</h3><hr>
1. <a href="https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository">Clone</a> the project<br><br>
2. Install dependencies [<a href="https://packaging.python.org/tutorials/installing-packages/">How to use pip</a>]<br><pre>pip install -r requirements.txt </pre>
3. To run the server <pre>python manage.py runserver</pre>
