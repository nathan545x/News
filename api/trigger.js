export default async function handler(req, res) {
  try {
    const response = await fetch(
      "https://api.github.com/repos/nathan545x/News/actions/workflows/news-alerts.yml/dispatches",
      {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
          "X-GitHub-Api-Version": "2022-11-28",
        },
        body: JSON.stringify({
          event_type: "run-rss",
        }),
      }
    );

    if (!response.ok) {
      return res.status(500).json({
        success: false,
        status: response.status,
      });
    }

    return res.status(200).json({
      success: true,
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      error: String(err),
    });
  }
}
