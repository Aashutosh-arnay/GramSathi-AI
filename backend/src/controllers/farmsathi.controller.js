
const { askFarmSathi } = require("../services/ai.service");

const askFarmSathiController = async (req, res) => {
    try {
        const { question, language = "hi" } = req.body;

        // Validate question
        if (!question || typeof question !== "string" || !question.trim()) {
            return res.status(400).json({
                success: false,
                message: "Question is required"
            });
        }

        // Validate question length
        if (question.length > 5000) {
            return res.status(400).json({
                success: false,
                message: "Question cannot exceed 5000 characters"
            });
        }

        // Validate language
        if (!["hi", "en"].includes(language)) {
            return res.status(400).json({
                success: false,
                message: "Language must be either hi or en"
            });
        }

        const result = await askFarmSathi(question, language);

        return res.status(200).json(result);

    }catch (error) {
        console.error("FarmSathi Controller Error:", error.message);

        return res.status(error.statusCode || 500).json({
            success: false,
            message: error.message || "FarmSathi AI is currently unavailable"
        });
    }
};

module.exports = { askFarmSathiController };
