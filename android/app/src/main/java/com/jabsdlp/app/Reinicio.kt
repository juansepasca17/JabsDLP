package com.jabsdlp.app

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.os.Process

/** Vive en el proceso ":reinicio". Cierra el proceso principal (si sigue vivo) y abre JabsDLP de nuevo. */
class Reinicio : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val pid = intent.getIntExtra(PID, -1)
        if (pid > 0 && pid != Process.myPid()) Process.killProcess(pid)
        startActivity(Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
        finish()
        Runtime.getRuntime().exit(0)
    }

    companion object {
        const val PID = "pid"
    }
}
