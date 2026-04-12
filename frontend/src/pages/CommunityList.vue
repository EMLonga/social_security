<template>
  <div class="community-list-page" style="margin-top: 70px; padding: 20px;">
    <div class="container">
      <h1>{{ t('communitiesReportsTitle') }}</h1>
      <div v-if="loading" class="loading">{{ t('loading') }}</div>
      <div v-else-if="communities.length === 0" class="empty-state">
        <p>{{ t('noCommunityReports') }}</p>
      </div>
      <div v-else class="community-grid">
        <div
          v-for="community in communities"
          :key="community.id"
          class="community-card"
        >
          <div class="community-card-content" @click="goToCommunity(community.id)">
            <h3>{{ community.name }}</h3>
            <p>{{ community.city }}, {{ community.state }}</p>
            <p>{{ t('safetyScore') }}: {{ community.safetyScore }}</p>
            <p>{{ t('safetyLevel') }}: {{ getSafetyLevelLabel(community.safetyLevel) }}</p>
            <p>
              {{ t('reportSummary') }}:
              {{ community.report?.highRiskPeriods || community.report?.highRiskLocations || t('noReportAvailable') }}
            </p>
          </div>
          <button class="btn btn-secondary" @click="goToCommunity(community.id)">
            {{ t('viewReport') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { communityService } from '../services/api'
import { useI18n } from '../utils/i18n'
import { ElMessage } from 'element-plus'
import { getSafetyLevelLabel } from '../utils/helpers'

const router = useRouter()
const { t } = useI18n()
const communities = ref([])
const loading = ref(false)

const loadCommunities = async () => {
  loading.value = true
  try {
    const res = await communityService.getCommunities({ page: 1, page_size: 20 })
    communities.value = res.data.communities || []
  } catch (error) {
    ElMessage.error('Failed to load community reports')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const goToCommunity = (id) => {
  router.push(`/communities/${id}`)
}

onMounted(() => {
  loadCommunities()
})
</script>

<style scoped>
.community-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.community-card {
  background-color: white;
  border: 1px solid #eaeaea;
  border-radius: 12px;
  padding: 20px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.community-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}

.community-card-content {
  cursor: pointer;
}

.community-card h3 {
  margin-bottom: 10px;
}

.community-card p {
  margin: 8px 0;
  color: #555;
}

.btn {
  margin-top: 15px;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: #888;
}
</style>
