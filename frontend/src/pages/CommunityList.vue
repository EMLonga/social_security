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
            <h3>{{ localizeCommunityName(community.name, community.state, community.city) }}</h3>
            <p>{{ localizeCommunityName(community.name, community.state, community.city) }}</p>
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
      <div v-if="total > pageSize" class="pagination-wrap">
        <el-pagination
          background
          layout="prev, pager, next, jumper, ->, total"
          :total="total"
          :current-page="currentPage"
          :page-size="pageSize"
          @current-change="handlePageChange"
        />
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
import { getSafetyLevelLabel, localizeCommunityName } from '../utils/helpers'

const router = useRouter()
const { t } = useI18n()
const communities = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const loadCommunities = async () => {
  loading.value = true
  try {
    const res = await communityService.getCommunities({
      page: currentPage.value,
      page_size: pageSize.value,
      sort_by: 'safety_score',
      sortOrder: 'desc',
    })
    communities.value = res.data.communities || []
    total.value = Number(res.data.total || 0)
  } catch (error) {
    ElMessage.error('Failed to load community reports')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadCommunities()
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

.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>
