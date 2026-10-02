package com.tarasca.uploader

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Tarasca uploader — receives bank extracts via Android's share sheet
 * and uploads them to Supabase Storage for the Streamlit app to import.
 */
class MainActivity : Activity() {

    private var sharedUri: Uri? = null
    private var sharedName: String = ""
    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        val uri = when (intent?.action) {
            Intent.ACTION_SEND -> intent.getParcelableExtra(Intent.EXTRA_STREAM)
            Intent.ACTION_SEND_MULTIPLE ->
                intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)?.firstOrNull()
            else -> null
        }
        if (uri == null) {
            renderNoFile()
            return
        }
        sharedUri = uri
        sharedName = getFileName(uri)
        renderFile()
    }

    private fun getFileName(uri: Uri): String {
        var name = uri.lastPathSegment ?: "extracto"
        contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0 && cursor.moveToFirst()) {
                cursor.getString(idx)?.let { name = it }
            }
        }
        return name
    }

    private fun renderNoFile() {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 48, 48, 48)
        }
        layout.addView(TextView(this).apply {
            text = "Tarasca"
            textSize = 24f
        })
        layout.addView(TextView(this).apply {
            text = "Compartí un extracto bancario con esta app para subirlo."
            textSize = 16f
        })
        setContentView(layout)
    }

    private fun renderFile() {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 48, 48, 48)
        }
        layout.addView(TextView(this).apply {
            text = "Tarasca"
            textSize = 24f
        })
        layout.addView(TextView(this).apply {
            text = "Archivo: $sharedName"
            textSize = 16f
        })
        layout.addView(Button(this).apply {
            text = "Subir a Tarasca"
            setOnClickListener { upload() }
        })
        statusText = TextView(this).apply { text = "" }
        layout.addView(statusText)
        setContentView(layout)
    }

    private fun upload() {
        val uri = sharedUri ?: return
        val name = sharedName
        statusText.text = "Subiendo..."
        Thread {
            try {
                val bytes = readBytes(uri)
                val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
                val safeName = name.replace(Regex("[^A-Za-z0-9._-]"), "_")
                val objectName = "${timestamp}_$safeName"
                val url = URL("${BuildConfig.SUPABASE_URL}/storage/v1/object/imports/$objectName")
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "PUT"
                conn.setRequestProperty("Authorization", "Bearer ${BuildConfig.SUPABASE_PUBLISHABLE_KEY}")
                conn.setRequestProperty("Content-Type", "application/octet-stream")
                conn.setRequestProperty("x-upsert", "true")
                conn.doOutput = true
                conn.outputStream.use { it.write(bytes) }
                val code = conn.responseCode
                runOnUiThread {
                    val msg = if (code in 200..299) "✅ Subido: $name" else "❌ Error $code"
                    statusText.text = msg
                    Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                runOnUiThread {
                    val msg = "❌ ${e.message}"
                    statusText.text = msg
                    Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    private fun readBytes(uri: Uri): ByteArray {
        val input: InputStream = contentResolver.openInputStream(uri)
            ?: throw IllegalArgumentException("No se puede leer el archivo")
        return input.use { it.readBytes() }
    }
}
