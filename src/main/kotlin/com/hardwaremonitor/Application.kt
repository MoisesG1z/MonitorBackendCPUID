package com.hardwaremonitor

import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.routing.*
import io.ktor.server.websocket.*
import io.ktor.websocket.*
import io.ktor.server.response.*
import io.ktor.server.http.content.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.serialization.gson.*
import java.time.Duration
import java.util.*
import java.util.concurrent.ConcurrentHashMap
import io.ktor.http.HttpStatusCode
import java.io.File

fun main() {
    val port = System.getenv("PORT")?.toInt() ?: 8080
    embeddedServer(Netty, port = port, host = "0.0.0.0", module = Application::module)
        .start(wait = true)
}

// Store active websocket sessions (Client ID -> Session)
val activeConnections = ConcurrentHashMap<String, DefaultWebSocketServerSession>()
// Store latest data from agents (Client ID -> JSON Data)
val agentData = ConcurrentHashMap<String, String>()

fun Application.module() {
    install(WebSockets) {
        pingPeriod = Duration.ofSeconds(15)
        timeout = Duration.ofSeconds(15)
        maxFrameSize = Long.MAX_VALUE
        masking = false
    }
    
    install(ContentNegotiation) {
        gson {
            setPrettyPrinting()
        }
    }

    routing {
        // Health check endpoint for UptimeRobot
        get("/") {
            call.respondText("Server is up and running!")
        }
        
        // Serve the Python agent download
        get("/download-agent") {
            val file = File("agent/agent.py")
            if (file.exists()) {
                call.response.header("Content-Disposition", "attachment; filename=\"agent.py\"")
                call.respondFile(file)
            } else {
                call.respond(HttpStatusCode.NotFound, "Agent file not found on server.")
            }
        }
        
        get("/api/data/{clientId}") {
            val clientId = call.parameters["clientId"] ?: return@get call.respond(HttpStatusCode.BadRequest, "Missing client id")
            val data = agentData[clientId]
            if (data != null) {
                call.respondText(data, io.ktor.http.ContentType.Application.Json)
            } else {
                call.respond(HttpStatusCode.NotFound, "No data for this client")
            }
        }

        // WebSocket endpoint for the Python agent to send data
        webSocket("/ws/agent/{clientId}") {
            val clientId = call.parameters["clientId"] ?: return@webSocket
            activeConnections[clientId] = this
            println("Agent connected: \$clientId")
            
            try {
                for (frame in incoming) {
                    if (frame is Frame.Text) {
                        val text = frame.readText()
                        agentData[clientId] = text
                        // Here we could also broadcast to connected web UI clients if we wanted real-time push
                    }
                }
            } catch (e: Exception) {
                println("Error with client \$clientId: \${e.message}")
            } finally {
                println("Agent disconnected: \$clientId")
                activeConnections.remove(clientId)
                // We keep the last known data in agentData for now, or clear it if offline
            }
        }
    }
}
