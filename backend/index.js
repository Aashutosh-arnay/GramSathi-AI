const express = require("express");

const app = express();

// Middleware
app.use(express.json());

// Health check API
app.get("/api/health", (req, res) => {
    res.status(200).json({
        success: true,
        message: "GramSathi AI Backend is running!"
    });
});

// Server configuration
const PORT = process.env.PORT || 5000;

// Start server
app.listen(PORT, () => {
    console.log(`GramSathi AI Backend running on port ${PORT}`);
});