export default async function handler(req, res) {
  try {
    const response = await fetch(
      "https://api.github.com/repos/nathan545x/News/actions/workflows/news-alerts.yml/dispatches",
      {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
        },
        body: JSON.stringify({
          ref: "main",
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
      message: "Workflow triggered",
    });

  } catch (err) {
    return res.status(500).json({
      success: false,
      error: String(err),
    });
  }
}