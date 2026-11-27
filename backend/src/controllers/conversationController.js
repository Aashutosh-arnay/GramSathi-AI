const mongoose = require("mongoose");
const Conversation = require("../models/Conversation");
const Message = require("../models/Message");
const Feedback = require("../models/Feedback");

// @desc    Create a new conversation
// @route   POST /api/conversations
// @access  Private

const createConversation = async (req, res) => {
  try {
    const { module, title } = req.body;

    // Validate module
    if (!["farmsathi", "nyayasathi"].includes(module)) {
      return res.status(400).json({
        success: false,
        message: "Module must be farmsathi or nyayasathi",
      });
    }

    // Validate optional title
    if (
      title !== undefined &&
      (typeof title !== "string" || !title.trim())
    ) {
      return res.status(400).json({
        success: false,
        message: "Title must be a non-empty string",
      });
    }

    // Create conversation
    const conversation = await Conversation.create({
      user: req.userId,
      module,
      title: title ? title.trim() : "New conversation",
    });

    return res.status(201).json({
      success: true,
      message: "Conversation created successfully",
      conversation,
    });
  } catch (error) {
    console.error("Create Conversation Error:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
};

const getConversations = async (req, res) => {
  try {
    const conversations = await Conversation.find({
      user: req.userId,
    }).sort({ updatedAt: -1 });

    return res.status(200).json({
      success: true,
      count: conversations.length,
      conversations,
    });
  } catch (error) {
    console.error("Get Conversations Error:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
};

const getConversationById = async (req, res) => {
  try {
    const { id } = req.params;

    // Validate conversation ID
    if (!mongoose.isValidObjectId(id)) {
      return res.status(400).json({
        success: false,
        message: "Invalid conversation ID",
      });
    }

    // Find conversation belonging to logged-in user
    const conversation = await Conversation.findOne({
      _id: id,
      user: req.userId,
    });

    if (!conversation) {
      return res.status(404).json({
        success: false,
        message: "Conversation not found",
      });
    }

    return res.status(200).json({
      success: true,
      message: "Conversation fetched successfully",
      conversation,
    });
  } catch (error) {
    console.error("Get Conversation Error:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
};


const deleteConversation = async (req, res) => {
  try {
    const { id } = req.params;

    // Validate conversation ID
    if (!mongoose.isValidObjectId(id)) {
      return res.status(400).json({
        success: false,
        message: "Invalid conversation ID",
      });
    }

    // Check conversation ownership
    const conversation = await Conversation.findOne({
      _id: id,
      user: req.userId,
    });

    if (!conversation) {
      return res.status(404).json({
        success: false,
        message: "Conversation not found",
      });
    }

    // Delete associated feedback
    await Feedback.deleteMany({
      conversation: conversation._id,
    });

    // Delete associated messages
    await Message.deleteMany({
      conversation: conversation._id,
    });

    // Delete conversation
    await Conversation.deleteOne({
      _id: conversation._id,
      user: req.userId,
    });

    return res.status(200).json({
      success: true,
      message: "Conversation deleted successfully",
    });
  } catch (error) {
    console.error("Delete Conversation Error:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
};

module.exports = {
  createConversation,
  getConversations,
  getConversationById,
  deleteConversation
};
