<template>
  <div class="auth-page">
    <div class="auth-container">
      <div class="auth-box">
        <div class="auth-logo">
          <h2>{{ t('authTitle') }}</h2>
        </div>

        <div class="tab-switch">
          <button :class="{ active: mode === 'login' }" @click="setMode('login')">{{ t('login') }}</button>
          <button :class="{ active: mode === 'register' }" @click="setMode('register')">{{ t('register') }}</button>
        </div>

        <form v-if="mode === 'login'" @submit.prevent="handleLogin" class="auth-form">
          <div class="form-group">
            <label>{{ t('usernameOrEmail') }}</label>
            <input v-model="loginForm.username" type="text" :placeholder="t('enterUsernameOrEmail')" required />
          </div>

          <div class="form-group">
            <label>{{ t('password') }}</label>
            <div class="password-input">
              <input
                v-model="loginForm.password"
                :type="showPassword ? 'text' : 'password'"
                :placeholder="t('enterPassword')"
                required
              />
              <button type="button" class="toggle-password" @click="showPassword = !showPassword">
                {{ showPassword ? t('hide') : t('show') }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>{{ t('captcha') }}</label>
            <div class="captcha-row">
              <input
                v-model="loginForm.captchaCode"
                type="text"
                :placeholder="t('enterCaptcha')"
                maxlength="8"
                required
              />
              <img
                v-if="captchaLogin.imageData"
                class="captcha-image"
                :src="captchaLogin.imageData"
                :alt="t('captcha')"
                @click="loadCaptcha('login')"
              />
              <button type="button" class="refresh-btn" @click="loadCaptcha('login')">{{ t('refreshCaptcha') }}</button>
            </div>
          </div>

          <button type="submit" class="btn btn-primary" :disabled="isLoading">
            {{ isLoading ? t('loggingIn') : t('login') }}
          </button>

          <div class="form-footer">
            <a href="#" @click.prevent="setMode('forgot')">{{ t('forgotPassword') }}</a>
          </div>
        </form>

        <form v-if="mode === 'register'" @submit.prevent="handleRegister" class="auth-form">
          <div class="form-group">
            <label>{{ t('username') }}</label>
            <input
              v-model="registerForm.username"
              type="text"
              :placeholder="t('usernameRuleHint')"
              @blur="validateUsernameField"
              required
            />
            <p v-if="usernameError" class="error-msg">{{ usernameError }}</p>
          </div>

          <div class="form-group">
            <label>{{ t('email') }}</label>
            <input
              v-model="registerForm.email"
              type="email"
              :placeholder="t('enterEmail')"
              @blur="validateEmailField"
              required
            />
            <p v-if="emailError" class="error-msg">{{ emailError }}</p>
          </div>

          <div class="form-group">
            <label>{{ t('password') }}</label>
            <div class="password-input">
              <input
                v-model="registerForm.password"
                :type="showPassword ? 'text' : 'password'"
                :placeholder="t('passwordRuleHint')"
                @blur="validatePasswordField"
                required
              />
              <button type="button" class="toggle-password" @click="showPassword = !showPassword">
                {{ showPassword ? t('hide') : t('show') }}
              </button>
            </div>
            <p v-if="passwordError" class="error-msg">{{ passwordError }}</p>
          </div>

          <div class="form-group">
            <label>{{ t('confirmPassword') }}</label>
            <input
              v-model="registerForm.confirmPassword"
              type="password"
              :placeholder="t('confirmPasswordHint')"
              @blur="validateConfirmPasswordField"
              required
            />
            <p v-if="confirmPasswordError" class="error-msg">{{ confirmPasswordError }}</p>
          </div>

          <div class="form-group">
            <label>{{ t('captcha') }}</label>
            <div class="captcha-row">
              <input
                v-model="registerForm.captchaCode"
                type="text"
                :placeholder="t('enterCaptcha')"
                maxlength="8"
                required
              />
              <img
                v-if="captchaRegister.imageData"
                class="captcha-image"
                :src="captchaRegister.imageData"
                :alt="t('captcha')"
                @click="loadCaptcha('register')"
              />
              <button type="button" class="refresh-btn" @click="loadCaptcha('register')">{{ t('refreshCaptcha') }}</button>
            </div>
          </div>

          <button type="submit" class="btn btn-primary" :disabled="isLoading || !isFormValid">
            {{ isLoading ? `${t('register')}...` : t('register') }}
          </button>
        </form>

        <form v-if="mode === 'forgot'" @submit.prevent="handleResetPassword" class="auth-form">
          <h3 class="forgot-title">{{ t('forgotPasswordTitle') }}</h3>

          <div class="form-group">
            <label>{{ t('usernameOrEmail') }}</label>
            <input v-model="forgotForm.account" type="text" :placeholder="t('enterUsernameOrEmail')" required />
          </div>

          <div class="form-group">
            <label>{{ t('captcha') }}</label>
            <div class="captcha-row">
              <input
                v-model="forgotForm.captchaCode"
                type="text"
                :placeholder="t('enterCaptcha')"
                maxlength="8"
                required
              />
              <img
                v-if="captchaForgot.imageData"
                :key="captchaForgot.imageKey"
                class="captcha-image"
                :src="captchaForgot.imageData"
                :alt="t('captcha')"
                @click="loadCaptcha('forgot')"
              />
              <button type="button" class="refresh-btn" @click="loadCaptcha('forgot')">{{ t('refreshCaptcha') }}</button>
            </div>
          </div>

          <div class="form-group code-group">
            <div class="code-input-wrap">
              <label>{{ t('verificationCode') }}</label>
              <input
                v-model="forgotForm.code"
                type="text"
                :placeholder="t('enterVerificationCode')"
                maxlength="6"
                required
              />
            </div>
            <button
              type="button"
              class="btn btn-secondary code-btn"
              :disabled="codeSending || sendCooldown > 0 || !forgotForm.account || !forgotForm.captchaCode"
              @click="sendResetCode"
            >
              {{ codeSending ? `${t('sendCode')}...` : sendCooldown > 0 ? `${sendCooldown}s` : t('sendCode') }}
            </button>
          </div>

          <div class="form-group">
            <label>{{ t('newPassword') }}</label>
            <input
              v-model="forgotForm.newPassword"
              :type="showPassword ? 'text' : 'password'"
              :placeholder="t('passwordRuleHint')"
              required
            />
          </div>

          <div class="form-group">
            <label>{{ t('confirmNewPassword') }}</label>
            <input
              v-model="forgotForm.confirmNewPassword"
              type="password"
              :placeholder="t('confirmPasswordHint')"
              required
            />
          </div>

          <button type="submit" class="btn btn-primary" :disabled="isLoading">
            {{ isLoading ? `${t('resetPassword')}...` : t('resetPassword') }}
          </button>

          <div class="form-footer">
            <a href="#" @click.prevent="setMode('login')">{{ t('backToLogin') }}</a>
          </div>
        </form>

        <div class="auth-footer">
          <a href="#">{{ t('privacyPolicy') }}</a> | <a href="#">{{ t('termsOfService') }}</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/app'
import { userService } from '../services/api'
import { validateEmail, validatePassword, validateUsername } from '../utils/helpers'
import { useI18n } from '../utils/i18n'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const { t } = useI18n()

const mode = ref(route.query.mode === 'register' ? 'register' : 'login')
const showPassword = ref(false)
const isLoading = ref(false)
const codeSending = ref(false)
const sendCooldown = ref(0)
let cooldownTimer = null

const captchaLogin = ref({ captchaId: '', imageData: '' })
const captchaRegister = ref({ captchaId: '', imageData: '' })
const captchaForgot = ref({ captchaId: '', imageData: '', imageKey: 0 })

const loginForm = ref({
  username: '',
  password: '',
  captchaCode: '',
})

const registerForm = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  captchaCode: '',
})

const forgotForm = ref({
  account: '',
  captchaCode: '',
  code: '',
  newPassword: '',
  confirmNewPassword: '',
})

const usernameError = ref('')
const emailError = ref('')
const passwordError = ref('')
const confirmPasswordError = ref('')

const isFormValid = computed(() => {
  return (
    registerForm.value.username &&
    registerForm.value.email &&
    registerForm.value.password &&
    registerForm.value.confirmPassword &&
    registerForm.value.captchaCode &&
    !usernameError.value &&
    !emailError.value &&
    !passwordError.value &&
    !confirmPasswordError.value
  )
})

const loadCaptcha = async (target = 'login') => {
  try {
    if (target === 'forgot') {
      captchaForgot.value = {
        ...captchaForgot.value,
        imageData: '',
        imageKey: Date.now(),
      }
    }
    const res = await userService.getCaptcha()
    const data = {
      captchaId: res.data.captcha_id,
      imageData: res.data.image_data,
    }
    if (target === 'login') captchaLogin.value = data
    if (target === 'register') captchaRegister.value = data
    if (target === 'forgot') captchaForgot.value = { ...data, imageKey: Date.now() }
  } catch (error) {
    ElMessage.error(t('captchaLoadFailed'))
  }
}

const setMode = async (nextMode) => {
  mode.value = nextMode
  if (nextMode === 'login') await loadCaptcha('login')
  if (nextMode === 'register') await loadCaptcha('register')
  if (nextMode === 'forgot') await loadCaptcha('forgot')
}

const validateUsernameField = () => {
  usernameError.value = validateUsername(registerForm.value.username) ? '' : t('usernameRule')
}

const validateEmailField = () => {
  emailError.value = validateEmail(registerForm.value.email) ? '' : t('validEmailRequired')
}

const validatePasswordField = () => {
  passwordError.value = validatePassword(registerForm.value.password) ? '' : t('passwordRule')
  validateConfirmPasswordField()
}

const validateConfirmPasswordField = () => {
  confirmPasswordError.value =
    registerForm.value.password === registerForm.value.confirmPassword ? '' : t('passwordsNotMatch')
}

const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password || !loginForm.value.captchaCode) {
    ElMessage.error(t('pleaseFillAllFields'))
    return
  }
  if (!captchaLogin.value.captchaId) {
    ElMessage.error(t('captchaLoadFailed'))
    return
  }

  isLoading.value = true
  try {
    const res = await userService.login({
      username: loginForm.value.username,
      password: loginForm.value.password,
      captcha_id: captchaLogin.value.captchaId,
      captcha_code: loginForm.value.captchaCode,
    })
    userStore.login(res.data.user, res.data.access_token)
    ElMessage.success(t('loginSuccessful'))
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirect)
  } catch (error) {
    ElMessage.error(`${t('loginFailed')}: ${error.response?.data?.detail || t('invalidCredentials')}`)
    await loadCaptcha('login')
    loginForm.value.captchaCode = ''
  } finally {
    isLoading.value = false
  }
}

const handleRegister = async () => {
  if (
    !registerForm.value.username ||
    !registerForm.value.email ||
    !registerForm.value.password ||
    !registerForm.value.confirmPassword ||
    !registerForm.value.captchaCode
  ) {
    ElMessage.error(t('pleaseFillAllFields'))
    return
  }

  if (!isFormValid.value) {
    ElMessage.error(t('pleaseFixErrors'))
    return
  }
  if (!captchaRegister.value.captchaId) {
    ElMessage.error(t('captchaLoadFailed'))
    return
  }

  isLoading.value = true
  try {
    await userService.register({
      username: registerForm.value.username,
      email: registerForm.value.email,
      password: registerForm.value.password,
      captcha_id: captchaRegister.value.captchaId,
      captcha_code: registerForm.value.captchaCode,
    })
    ElMessage.success(t('registrationSuccessful'))
    mode.value = 'login'
    registerForm.value = {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      captchaCode: '',
    }
    await loadCaptcha('login')
  } catch (error) {
    ElMessage.error(`${t('registrationFailed')}: ${error.response?.data?.detail || t('unknownError')}`)
    await loadCaptcha('register')
    registerForm.value.captchaCode = ''
  } finally {
    isLoading.value = false
  }
}

const sendResetCode = async () => {
  if (!forgotForm.value.account || !forgotForm.value.captchaCode) {
    ElMessage.error(t('pleaseFillAllFields'))
    return
  }
  if (!captchaForgot.value.captchaId) {
    ElMessage.error(t('captchaLoadFailed'))
    return
  }

  codeSending.value = true
  try {
    const res = await userService.sendPasswordResetCode({
      account: forgotForm.value.account,
      captcha_id: captchaForgot.value.captchaId,
      captcha_code: forgotForm.value.captchaCode,
    })
    const debugCode = res?.data?.debug_code
    if (debugCode) {
      forgotForm.value.code = String(debugCode)
      ElMessage.success(`Verification code: ${debugCode}`)
    } else {
      ElMessage.success(t('codeSent'))
    }
    forgotForm.value.captchaCode = ''
    await loadCaptcha('forgot')
    startSendCooldown(30)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('actionFailed'))
    forgotForm.value.captchaCode = ''
    await loadCaptcha('forgot')
  } finally {
    codeSending.value = false
  }
}

const startSendCooldown = (seconds = 30) => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
  sendCooldown.value = seconds
  cooldownTimer = setInterval(() => {
    sendCooldown.value -= 1
    if (sendCooldown.value <= 0) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
      sendCooldown.value = 0
    }
  }, 1000)
}

const handleResetPassword = async () => {
  if (
    !forgotForm.value.account ||
    !forgotForm.value.code ||
    !forgotForm.value.newPassword ||
    !forgotForm.value.confirmNewPassword
  ) {
    ElMessage.error(t('pleaseFillAllFields'))
    return
  }
  if (!validatePassword(forgotForm.value.newPassword)) {
    ElMessage.error(t('passwordRule'))
    return
  }
  if (forgotForm.value.newPassword !== forgotForm.value.confirmNewPassword) {
    ElMessage.error(t('passwordsNotMatch'))
    return
  }

  isLoading.value = true
  try {
    await userService.confirmPasswordReset({
      account: forgotForm.value.account,
      code: forgotForm.value.code,
      new_password: forgotForm.value.newPassword,
    })
    ElMessage.success(t('passwordResetSuccess'))
    forgotForm.value = {
      account: '',
      captchaCode: '',
      code: '',
      newPassword: '',
      confirmNewPassword: '',
    }
    await setMode('login')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('actionFailed'))
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  if (userStore.isLoggedIn) {
    router.push('/')
    return
  }
  await loadCaptcha('login')
  await loadCaptcha('register')
  await loadCaptcha('forgot')
})

onBeforeUnmount(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
})
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.auth-container {
  width: 100%;
  max-width: 430px;
}

.auth-box {
  background-color: white;
  border-radius: 8px;
  padding: 36px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.auth-logo {
  text-align: center;
  margin-bottom: 26px;
}

.auth-logo h2 {
  color: #333;
  margin: 0;
}

.tab-switch {
  display: flex;
  gap: 10px;
  margin-bottom: 26px;
  border-bottom: 2px solid #f0f0f0;
}

.tab-switch button {
  flex: 1;
  padding: 10px;
  background: none;
  border: none;
  color: #999;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.3s;
  margin-bottom: -2px;
}

.tab-switch button.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.auth-form {
  display: flex;
  flex-direction: column;
}

.forgot-title {
  margin-bottom: 16px;
  color: #374151;
  font-size: 18px;
}

.form-group {
  margin-bottom: 18px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.captcha-row {
  display: grid;
  grid-template-columns: 1fr 120px auto;
  gap: 8px;
  align-items: center;
}

.captcha-image {
  width: 120px;
  height: 42px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.refresh-btn {
  height: 40px;
  border: 1px solid #cdd6e4;
  border-radius: 6px;
  background: #f8fafc;
  color: #334155;
  cursor: pointer;
  padding: 0 10px;
  font-size: 12px;
}

.password-input {
  position: relative;
  display: flex;
  align-items: center;
}

.password-input input {
  flex: 1;
}

.toggle-password {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
  padding: 5px;
}

.code-group {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: end;
}

.code-input-wrap label {
  display: block;
}

.code-btn {
  height: 40px;
  margin-bottom: 0;
}

.btn {
  padding: 10px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background-color: #667eea;
  color: white;
  margin-top: 6px;
}

.btn-secondary {
  background-color: #e2e8f0;
  color: #334155;
}

.btn-primary:hover:not(:disabled) {
  background-color: #764ba2;
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-msg {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 4px;
  margin-bottom: 0;
}

.form-footer {
  text-align: center;
  margin-top: 15px;
}

.form-footer a {
  color: #667eea;
  font-size: 13px;
  text-decoration: none;
}

.form-footer a:hover {
  text-decoration: underline;
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  font-size: 12px;
  color: #999;
}

.auth-footer a {
  color: #667eea;
  text-decoration: none;
}

.auth-footer a:hover {
  text-decoration: underline;
}

@media (max-width: 480px) {
  .auth-box {
    padding: 20px;
  }

  .captcha-row {
    grid-template-columns: 1fr;
  }

  .captcha-image {
    width: 100%;
    height: 44px;
  }

  .code-group {
    grid-template-columns: 1fr;
  }
}
</style>
