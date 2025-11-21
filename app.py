from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import io
import math

app = Flask(__name__)

# ----- OOP class -----
class SpotifyHistory:
    """
    Loads a Spotify StreamingHistory JSON file (list of plays).
    Expects fields: trackName, artistName, msPlayed
    """
    def __init__(self, file_like):
        # file_like can be an open file or BytesIO
        try:
            self.df = pd.read_json(file_like)
        except ValueError:
            # sometimes Spotify exports line-delimited JSON
            file_like.seek(0)
            self.df = pd.read_json(file_like, lines=True)

        # sanity: keep only expected columns
        cols = ["trackName", "artistName", "msPlayed"]
        self.df = self.df[[c for c in cols if c in self.df.columns]].copy()
        # convert ms -> minutes (float)
        if "msPlayed" in self.df.columns:
            self.df["minutes"] = self.df["msPlayed"].astype(float) / 60000.0
        else:
            self.df["minutes"] = 0.0

    def total_minutes(self):
        return int(self.df["minutes"].sum())  # total whole minutes

    def top_song(self):
        if self.df.empty:
            return None
        grouped = (self.df
                   .groupby(["trackName", "artistName"], as_index=False)
                   .agg({"minutes": "sum"}))
        top = grouped.sort_values("minutes", ascending=False).iloc[0]
        return {"song": top["trackName"], "artist": top["artistName"],
                "mins": int(top["minutes"])}

    def top_artist(self):
        if self.df.empty:
            return None
        g = self.df.groupby("artistName", as_index=False).agg({"minutes": "sum"})
        top = g.sort_values("minutes", ascending=False).iloc[0]
        return {"artist": top["artistName"], "mins": int(top["minutes"])}

    def top_3_songs(self, n=3):
        if self.df.empty:
            return []
        grouped = (self.df
                   .groupby(["trackName", "artistName"], as_index=False)
                   .agg({"minutes": "sum"}))
        topn = grouped.sort_values("minutes", ascending=False).head(n)
        return [{"song": r["trackName"], "artist": r["artistName"], "mins": int(r["minutes"])}
                for _, r in topn.iterrows()]


# ----- Routes -----
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    # ensure file present
    f = request.files.get("file")
    if not f:
        return redirect(url_for("index"))

    # read into BytesIO so pandas can read multiple times if needed
    stream = io.BytesIO(f.read())
    stream.seek(0)

    stats = SpotifyHistory(stream)

    total = stats.total_minutes()
    top_song = stats.top_song()
    top_artist = stats.top_artist()
    top3 = stats.top_3_songs()

    return render_template(
        "result.html",
        total=total,
        top_song=top_song,
        top_artist=top_artist,
        top3=top3
    )


if __name__ == "__main__":
    app.run(debug=True)
