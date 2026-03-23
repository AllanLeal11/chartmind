export default async function handler(req, res) {
  try {
    // validar método
    if (req.method !== "POST") {
      return res.status(405).json({ error: "Método no permitido" });
    }

    const apiKey = process.env.API_KEY;

    if (!apiKey) {
      throw new Error("API KEY no definida");
    }

    const response = await fetch(`https://api.tuapi.com/data?apikey=${apiKey}`);

    if (!response.ok) {
      throw new Error(`Error API externa: ${response.status}`);
    }

    const data = await response.json();

    return res.status(200).json(data);

  } catch (error) {
    console.error("ERROR EN /api/analyze:", error);
    return res.status(500).json({
      error: error.message || "Error interno"
    });
  }
}
