const SpotifyWebApi = require("spotify-web-api-node");

function getSpotifyClient() {
  const clientId = process.env.SPOTIFY_CLIENT_ID;
  const clientSecret = process.env.SPOTIFY_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    return null;
  }

  return new SpotifyWebApi({
    clientId: clientId,
    clientSecret: clientSecret,
  });
}

async function authenticate(spotify) {
  const data = await spotify.clientCredentialsGrant();
  spotify.setAccessToken(data.body.access_token);
}

exports.handler = async function (event) {
  const playlistId =
    event.queryStringParameters && event.queryStringParameters.id;

  if (!playlistId) {
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "error",
        message: "Please provide a playlist ID.",
      }),
    };
  }

  const spotify = getSpotifyClient();

  if (!spotify) {
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "error",
        message:
          "Spotify API credentials are not configured. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.",
      }),
    };
  }

  try {
    await authenticate(spotify);

    const playlist = await spotify.getPlaylist(playlistId);
    const playlistName = playlist.body.name;

    // Fetch tracks (up to 100 per request)
    const trackItems = playlist.body.tracks.items || [];
    const tracks = trackItems
      .filter(function (item) {
        return item.track && item.track.type === "track";
      })
      .map(function (item) {
        const track = item.track;
        return {
          name: track.name,
          artists: track.artists.map(function (a) { return a.name; }).join(", "),
          album: track.album.name,
          duration_ms: track.duration_ms,
        };
      });

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "success",
        playlist_name: playlistName,
        tracks: tracks,
      }),
    };
  } catch (error) {
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "error",
        message: "Failed to load playlist: " + error.message,
      }),
    };
  }
};
