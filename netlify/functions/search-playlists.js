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
  const query = event.queryStringParameters && event.queryStringParameters.q;

  if (!query) {
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "error",
        message: "Please provide a search query.",
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

    const results = await spotify.searchPlaylists(query, { limit: 10 });
    const items = results.body.playlists.items || [];

    const playlists = items
      .filter(function (item) {
        return item && item.public !== false;
      })
      .map(function (item) {
        const image =
          item.images && item.images.length > 0 ? item.images[0].url : null;
        return {
          name: item.name,
          url: item.external_urls.spotify,
          tracks: item.tracks.total,
          owner: item.owner.display_name || item.owner.id,
          image: image,
        };
      });

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "success",
        playlists: playlists,
        count: playlists.length,
      }),
    };
  } catch (error) {
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "error",
        message: "Search failed: " + error.message,
      }),
    };
  }
};
