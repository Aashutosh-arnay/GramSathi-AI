
const mongoose = require("mongoose");
const Conversation = require("../models/Conversation");
const Message = require("../models/Message");

// @desc    Add a user message to a conversation
// @route   POST /api/conversations/:id/messages
// @access  Private

const addMessage = async (req, res) => {
  try {
    const { id } = req.params;
    const { content } = req.body;

    // Validate conversation ID
    if (!mongoose.isValidObjectId(id)) {
      return res.status(400).json({
        success: false,
        message: "Invalid conversation ID",
      });
    }

    // Validate message content
    if (
      typeof content !== "string" ||
      !content.trim()
    ) {
      return res.status(400).json({
        success: false,
        message: "Message content is required",
      });
    }

    if (content.trim().length > 10000) {
      return res.status(400).json({
        success: false,
        message: "Message cannot exceed 10000 characters",
      });
    }

    // Verify conversation ownership
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

    // Create user message
    const message = await Message.create({
      conversation: conversation._id,
      role: "user",
      content: content.trim(),
    });

    // Update conversation activity timestamp
    conversation.updatedAt = new Date();
    await conversation.save();

    return res.status(201).json({
      success: true,
      message: "Message added successfully",
      data: message,
    });
  } catch (error) {
    console.error("Add Message Error:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
};

const getMessages = async (req, res) => {
  try {
    const { id } = req.params;

    // Validate conversation ID
    if (!mongoose.isValidObjectId(id)) {
      return res.status(400).json({
        success: false,
        message: "Invalid conversation ID",
      });
    }

    // Verify conversation ownership
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

    // Retrieve messages in chronological order
    const messages = await Message.find({
      conversation: conversation._id,
    }).sort({ createdAt: 1 });

    return res.status(200).json({
      success: true,
      count: messages.length,
      messages,
    });
  } catch (error) {
    console.error("Get Messages Error:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
};

module.exports = { addMessage, getMessages };
