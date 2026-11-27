
const axios = require("axios");

const AI_SERVICE_URL =
    process.env.AI_SERVICE_URL || "http://127.0.0.1:8000";

const aiClient = axios.create({
    baseURL: AI_SERVICE_URL,
    timeout: 60000
});

const sendAIRequest = async (endpoint, payload) => {
    try {
        const response = await aiClient.post(endpoint, payload);
        return response.data;

    } catch (error) {
        const serviceError = new Error("AI service request failed");

        if (
            error.code === "ECONNABORTED" ||
            error.code === "ETIMEDOUT"
        ) {
            serviceError.statusCode = 504;
            serviceError.message = "AI service request timed out";

        } else if (error.response) {
            serviceError.statusCode =
                error.response.status >= 500 ? 503 : 502;

            serviceError.message = "AI service returned an error";

        } else {
            serviceError.statusCode = 503;
            serviceError.message = "AI service is unavailable";
        }

        throw serviceError;
    }
};

const askFarmSathi = async (question, language = "hi") => {
    return sendAIRequest("/api/farmsathi/ask", {
        question,
        language
    });
};

const askNyayaSathi = async (question, language = "hi") => {
    return sendAIRequest("/api/nyayasathi/ask", {
        question,
        language
    });
};

module.exports = {
    askFarmSathi,
    askNyayaSathi
};
