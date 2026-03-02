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

exports.handler = async function () {
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
    await spotify.searchArtists("test", { limit: 1 });

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "success",
        message: "Spotify API connection is working!",
      }),
    };
  } catch (error) {
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "error",
        message: "Spotify connection failed: " + error.message,
      }),
    };
  }
};
